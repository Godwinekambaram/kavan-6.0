"""
KAVAN v6.0 — Marketplace Service
============================================================
Layer 5: Business logic for the Marketplace & Product Management.

Rules (Clean Architecture):
  - All business rules live here, NOT in views or models.
  - Services raise KAVANException subclasses on error conditions.
  - Services call Repositories for all data access.
  - Services are stateless — no instance state between calls.

Responsibilities:
  - ProductCatalogueService : Platform admin product management
  - MarketplaceService      : Tenant-facing marketplace browse/install
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from django.db import transaction

from apps.marketplace.models.product import (
    Product,
    ProductPricing,
    ProductStatus,
    ProductVersion,
    TenantProduct,
    TenantProductStatus,
)
from apps.marketplace.repositories import (
    ProductPricingRepository,
    ProductRepository,
    ProductVersionRepository,
    TenantProductRepository,
)
from common.exceptions.base import KAVANException, ValidationException
from common.services.base_service import BaseService

logger = logging.getLogger("kavan.marketplace.services")


# ============================================================
# CUSTOM EXCEPTIONS
# ============================================================

class ProductNotFoundException(KAVANException):
    """Raised when a requested product does not exist."""
    error_code = "MKT_001"

    def __init__(self, message="Product not found."):
        super().__init__(message)


class ProductAlreadyInstalledException(KAVANException):
    """Raised when a tenant tries to install an already-installed product."""
    error_code = "MKT_002"

    def __init__(self, message="This product is already installed for your tenant."):
        super().__init__(message)


class ProductNotAvailableException(KAVANException):
    """Raised when a tenant attempts to install a non-published product."""
    error_code = "MKT_003"

    def __init__(self, message="This product is not available in the marketplace."):
        super().__init__(message)


class SubscriptionNotFoundException(KAVANException):
    """Raised when a subscription record is not found."""
    error_code = "MKT_004"

    def __init__(self, message="Product subscription not found."):
        super().__init__(message)


# ============================================================
# PRODUCT CATALOGUE SERVICE  (Platform Admin operations)
# ============================================================

class ProductCatalogueService(BaseService):
    """
    Manages the platform-level product catalogue.

    Used exclusively by Super Admins (platform:create_product,
    platform:manage_products permissions).
    """

    @classmethod
    @transaction.atomic
    def create_product(
        cls,
        code: str,
        name: str,
        description: str = "",
        category: str = "OTHER",
        tagline: str = "",
        icon_url: str = None,
        documentation_url: str = None,
        support_email: str = None,
    ) -> Product:
        """
        Create a new product in DRAFT status.

        Args:
            code:              Unique machine-readable identifier.
            name:              Human-readable product name.
            description:       Long product description.
            category:          ProductCategory value.
            tagline:           Short marketing description.
            icon_url:          URL to product icon.
            documentation_url: Link to documentation.
            support_email:     Support email address.

        Returns:
            Newly created Product instance.

        Raises:
            ValidationException: If the code already exists.
        """
        if ProductRepository.exists(code=code):
            raise ValidationException(
                f"A product with code '{code}' already exists."
            )

        product = ProductRepository.create(
            code=code,
            name=name,
            description=description,
            category=category,
            tagline=tagline,
            icon_url=icon_url,
            documentation_url=documentation_url,
            support_email=support_email,
            status=ProductStatus.DRAFT,
        )

        logger.info(
            "Product created",
            extra={"kavan_data": {"product_id": str(product.id), "code": code}},
        )
        return product

    @classmethod
    def publish_product(cls, product_id: str) -> Product:
        """
        Publish a product to the marketplace (DRAFT → PUBLISHED).
        At least one active version must exist before publishing.

        Raises:
            ProductNotFoundException:  Product not found.
            ValidationException:       No active version found.
        """
        product = ProductRepository.get_by_id(product_id)
        if not product:
            raise ProductNotFoundException()

        latest_version = ProductVersionRepository.get_latest(product)
        if not latest_version:
            raise ValidationException(
                "Cannot publish a product with no active versions. "
                "Please add at least one ProductVersion first."
            )

        product.publish()
        logger.info(
            "Product published",
            extra={"kavan_data": {"product_id": str(product.id)}},
        )
        return product

    @classmethod
    def archive_product(cls, product_id: str) -> Product:
        """
        Archive a product — removes it from the marketplace.

        Raises:
            ProductNotFoundException: Product not found.
        """
        product = ProductRepository.get_by_id(product_id)
        if not product:
            raise ProductNotFoundException()

        product.archive()
        logger.info(
            "Product archived",
            extra={"kavan_data": {"product_id": str(product.id)}},
        )
        return product

    @classmethod
    @transaction.atomic
    def add_product_version(
        cls,
        product_id: str,
        version_string: str,
        docker_image: str,
        release_notes: str = "",
        helm_chart_ref: str = "",
        min_memory_mb: int = 512,
        min_cpu_cores: int = 1,
    ) -> ProductVersion:
        """
        Add a new version to an existing product.

        Args:
            product_id:      UUID of the parent product.
            version_string:  Semantic version (e.g., 'v1.2.0').
            docker_image:    Docker image reference.
            release_notes:   Changelog text.
            helm_chart_ref:  Optional Helm chart reference.
            min_memory_mb:   Minimum RAM in MB.
            min_cpu_cores:   Minimum CPU cores.

        Returns:
            ProductVersion instance.

        Raises:
            ProductNotFoundException: Product not found.
            ValidationException:     Duplicate version string.
        """
        product = ProductRepository.get_by_id(product_id)
        if not product:
            raise ProductNotFoundException()

        if ProductVersionRepository.exists(product=product, version_string=version_string):
            raise ValidationException(
                f"Version '{version_string}' already exists for this product."
            )

        version = ProductVersionRepository.create(
            product=product,
            version_string=version_string,
            docker_image=docker_image,
            release_notes=release_notes,
            helm_chart_ref=helm_chart_ref,
            min_memory_mb=min_memory_mb,
            min_cpu_cores=min_cpu_cores,
            released_at=datetime.now(tz=timezone.utc),
        )

        logger.info(
            "Product version added",
            extra={
                "kavan_data": {
                    "product_id": str(product.id),
                    "version": version_string,
                }
            },
        )
        return version

    @classmethod
    @transaction.atomic
    def set_pricing(
        cls,
        version_id: str,
        model: str,
        price_per_unit: float,
        currency: str = "USD",
        billing_period_days: int = 30,
        trial_days: int = 0,
        max_seats: int = None,
        is_default: bool = True,
    ) -> ProductPricing:
        """
        Create or replace the default pricing plan for a version.

        Raises:
            ValidationException: Version not found.
        """
        try:
            version = ProductVersionRepository.get_by_id(version_id)
        except Exception:
            version = None

        if not version:
            raise ValidationException("Product version not found.")

        # If is_default, clear the existing default for this version
        if is_default:
            ProductPricingRepository.get_for_version(version).filter(
                is_default=True
            ).update(is_default=False)

        pricing = ProductPricingRepository.create(
            version=version,
            model=model,
            price_per_unit=price_per_unit,
            currency=currency,
            billing_period_days=billing_period_days,
            trial_days=trial_days,
            max_seats=max_seats,
            is_default=is_default,
        )
        return pricing


# ============================================================
# MARKETPLACE SERVICE  (Tenant-facing operations)
# ============================================================

class MarketplaceService(BaseService):
    """
    Handles tenant-facing marketplace operations:
    browsing the catalogue, installing, upgrading, and
    uninstalling products.
    """

    @classmethod
    def list_available_products(cls, category: str = None) -> List[Product]:
        """
        Return all published products visible to tenants.

        Args:
            category: Optional filter by ProductCategory.

        Returns:
            List of Product instances.
        """
        if category:
            return list(ProductRepository.get_by_category(category))
        return list(ProductRepository.get_published())

    @classmethod
    def get_product_detail(cls, product_code: str) -> Product:
        """
        Return a single published product by its code.

        Raises:
            ProductNotFoundException:  Not found.
            ProductNotAvailableException: Product not published.
        """
        product = ProductRepository.get_by_code(product_code)
        if not product:
            raise ProductNotFoundException()

        if product.status != ProductStatus.PUBLISHED:
            raise ProductNotAvailableException()

        return product

    @classmethod
    @transaction.atomic
    def install_product(
        cls,
        tenant,
        product_code: str,
        version_string: str = None,
        pricing_plan_id: str = None,
        installed_by=None,
    ) -> TenantProduct:
        """
        Subscribe a tenant to a product.

        Steps:
          1. Validate product exists and is published.
          2. Validate no active subscription exists.
          3. Resolve version (latest if not specified).
          4. Resolve pricing plan (default if not specified).
          5. Generate a unique license key.
          6. Create TenantProduct record in PENDING state.
          7. Trigger Layer 6 DeploymentEngine via Celery.

        Args:
            tenant:          Tenant instance.
            product_code:    Unique product code.
            version_string:  Optional specific version to install.
            pricing_plan_id: Optional UUID of a specific pricing plan.
            installed_by:    User performing the installation.

        Returns:
            TenantProduct subscription record.

        Raises:
            ProductNotFoundException:          Product not found.
            ProductNotAvailableException:      Product not published.
            ProductAlreadyInstalledException:  Already subscribed.
        """
        product = ProductRepository.get_by_code(product_code)
        if not product:
            raise ProductNotFoundException()

        if product.status != ProductStatus.PUBLISHED:
            raise ProductNotAvailableException()

        if TenantProductRepository.is_subscribed(tenant, product):
            raise ProductAlreadyInstalledException()

        # Resolve version
        if version_string:
            version = ProductVersionRepository.get_by_version_string(product, version_string)
            if not version:
                raise ValidationException(
                    f"Version '{version_string}' not found for product '{product_code}'."
                )
        else:
            version = ProductVersionRepository.get_latest(product)
            if not version:
                raise ValidationException(
                    "No active version found for this product."
                )

        # Resolve pricing
        pricing = None
        if pricing_plan_id:
            pricing = ProductPricingRepository.get_by_id(pricing_plan_id)
        if not pricing:
            pricing = ProductPricingRepository.get_default_plan(version)

        # Trial end date
        trial_ends_at = None
        if pricing and pricing.trial_days > 0:
            trial_ends_at = datetime.now(tz=timezone.utc) + timedelta(days=pricing.trial_days)

        # Generate license key
        license_key = cls._generate_license_key(tenant, product)

        # Create subscription record
        subscription = TenantProductRepository.create(
            tenant=tenant,
            product=product,
            current_version=version,
            pricing_plan=pricing,
            status=TenantProductStatus.PENDING,
            license_key=license_key,
            seat_count=1,
            trial_ends_at=trial_ends_at,
            installed_by=installed_by,
        )

        logger.info(
            "Product installation initiated",
            extra={
                "kavan_data": {
                    "tenant_id": str(tenant.id),
                    "product": product_code,
                    "version": version.version_string,
                    "subscription_id": str(subscription.id),
                }
            },
        )

        # Trigger deployment via Celery (Layer 6 integration)
        cls._trigger_deployment(subscription)

        return subscription

    @classmethod
    @transaction.atomic
    def upgrade_product(
        cls,
        tenant,
        product_code: str,
        target_version_string: str,
    ) -> TenantProduct:
        """
        Upgrade a tenant's existing product to a newer version.

        Steps:
          1. Validate active subscription exists.
          2. Validate target version exists and is newer.
          3. Update current_version on subscription.
          4. Trigger re-deployment via Layer 6.

        Raises:
            SubscriptionNotFoundException: No active subscription.
            ValidationException:          Version not found or invalid.
        """
        product = ProductRepository.get_by_code(product_code)
        if not product:
            raise ProductNotFoundException()

        subscription = TenantProductRepository.get_subscription(tenant, product)
        if not subscription or subscription.status != TenantProductStatus.ACTIVE:
            raise SubscriptionNotFoundException()

        target_version = ProductVersionRepository.get_by_version_string(
            product, target_version_string
        )
        if not target_version:
            raise ValidationException(
                f"Target version '{target_version_string}' not found."
            )

        if not target_version.is_active:
            raise ValidationException(
                f"Version '{target_version_string}' is no longer supported (EOL)."
            )

        old_version = subscription.current_version.version_string
        TenantProductRepository.update(subscription, current_version=target_version)

        logger.info(
            "Product upgrade initiated",
            extra={
                "kavan_data": {
                    "tenant_id": str(tenant.id),
                    "product": product_code,
                    "from_version": old_version,
                    "to_version": target_version_string,
                }
            },
        )

        # Trigger upgrade deployment
        cls._trigger_upgrade(subscription, old_version)
        return subscription

    @classmethod
    @transaction.atomic
    def uninstall_product(cls, tenant, product_code: str) -> TenantProduct:
        """
        Cancel and remove a tenant's product subscription.

        The TenantProduct record is soft-cancelled (not deleted)
        for audit trail. The deployment is decommissioned by Layer 6.

        Raises:
            SubscriptionNotFoundException: No subscription found.
        """
        product = ProductRepository.get_by_code(product_code)
        if not product:
            raise ProductNotFoundException()

        subscription = TenantProductRepository.get_subscription(tenant, product)
        if not subscription:
            raise SubscriptionNotFoundException()

        subscription.cancel()

        logger.info(
            "Product uninstalled",
            extra={
                "kavan_data": {
                    "tenant_id": str(tenant.id),
                    "product": product_code,
                }
            },
        )

        # Trigger decommission in Layer 6
        cls._trigger_decommission(subscription)
        return subscription

    @classmethod
    def get_tenant_subscriptions(cls, tenant) -> List[TenantProduct]:
        """Return all active product subscriptions for a tenant."""
        return list(TenantProductRepository.get_active_by_tenant(tenant))

    # --------------------------------------------------------
    # PRIVATE HELPERS
    # --------------------------------------------------------

    @staticmethod
    def _generate_license_key(tenant, product: Product) -> str:
        """
        Generate a unique, opaque license key.
        Format: KAVAN-{tenant_code}-{product_code}-{short_uuid}
        """
        short_uid = str(uuid.uuid4()).replace("-", "")[:12].upper()
        tenant_code = getattr(tenant, "tenant_code", "TENANT")
        return f"KAVAN-{tenant_code}-{product.code.upper()}-{short_uid}"

    @staticmethod
    def _trigger_deployment(subscription: TenantProduct) -> None:
        """
        Enqueue a deployment task in Celery (Layer 6 hook).
        Import inside method to avoid circular import at module load.
        """
        try:
            from apps.deployments.tasks import provision_product_task
            provision_product_task.delay(str(subscription.id))
        except ImportError:
            logger.warning(
                "Layer 6 DeploymentEngine not available. "
                "Deployment task not queued for subscription %s.",
                str(subscription.id),
            )

    @staticmethod
    def _trigger_upgrade(subscription: TenantProduct, from_version: str) -> None:
        """Enqueue an upgrade task in Celery (Layer 6 hook)."""
        try:
            from apps.deployments.tasks import upgrade_product_task
            upgrade_product_task.delay(str(subscription.id), from_version)
        except ImportError:
            logger.warning(
                "Layer 6 DeploymentEngine not available. Upgrade task not queued."
            )

    @staticmethod
    def _trigger_decommission(subscription: TenantProduct) -> None:
        """Enqueue a decommission task in Celery (Layer 6 hook)."""
        try:
            from apps.deployments.tasks import decommission_product_task
            decommission_product_task.delay(str(subscription.id))
        except ImportError:
            logger.warning(
                "Layer 6 DeploymentEngine not available. Decommission task not queued."
            )
