"""
KAVAN v6.0 — Marketplace Repository
============================================================
Layer 5: Data access abstraction for marketplace models.

Rules (Clean Architecture):
  - Repositories contain ONLY database access — no business logic.
  - All query methods return model instances or QuerySets.
  - Services call these methods; views never touch the ORM directly.
"""

import logging
import uuid
from typing import List, Optional

from django.db.models import QuerySet

from apps.marketplace.models.product import (
    Product,
    ProductPricing,
    ProductStatus,
    ProductVersion,
    TenantProduct,
    TenantProductStatus,
)
from common.repositories.base_repository import BaseRepository

logger = logging.getLogger("kavan.marketplace.repositories")


class ProductRepository(BaseRepository):
    """
    Repository for Product model — platform-level catalogue access.
    """

    model = Product

    @classmethod
    def get_published(cls) -> QuerySet:
        """Return all published (visible) products."""
        return cls.get_queryset().filter(status=ProductStatus.PUBLISHED)

    @classmethod
    def get_featured(cls) -> QuerySet:
        """Return featured products for marketplace homepage."""
        return cls.get_published().filter(is_featured=True)

    @classmethod
    def get_by_code(cls, code: str) -> Optional[Product]:
        """Fetch a product by its unique machine code."""
        try:
            return cls.get_queryset().get(code=code)
        except Product.DoesNotExist:
            return None

    @classmethod
    def get_by_category(cls, category: str) -> QuerySet:
        """Return all published products in a given category."""
        return cls.get_published().filter(category=category)

    @classmethod
    def search(cls, query: str) -> QuerySet:
        """Basic full-text search across name, tagline, and description."""
        return cls.get_published().filter(
            models_Q_name__icontains=query
        )


class ProductVersionRepository(BaseRepository):
    """
    Repository for ProductVersion — immutable release records.
    """

    model = ProductVersion

    @classmethod
    def get_active_versions(cls, product: Product) -> QuerySet:
        """Return all active (non-EOL) versions for a product."""
        return cls.get_queryset().filter(
            product=product,
            is_active=True,
        ).order_by("-released_at")

    @classmethod
    def get_latest(cls, product: Product) -> Optional[ProductVersion]:
        """Return the most recently released active version."""
        return (
            cls.get_queryset()
            .filter(product=product, is_active=True)
            .order_by("-released_at", "-created_at")
            .first()
        )

    @classmethod
    def get_by_version_string(cls, product: Product, version_string: str) -> Optional[ProductVersion]:
        """Fetch a specific version by product + version string."""
        try:
            return cls.get_queryset().get(
                product=product,
                version_string=version_string,
            )
        except ProductVersion.DoesNotExist:
            return None


class ProductPricingRepository(BaseRepository):
    """
    Repository for ProductPricing — pricing plan access.
    """

    model = ProductPricing

    @classmethod
    def get_for_version(cls, version: ProductVersion) -> QuerySet:
        """Return all pricing plans for a version."""
        return cls.get_queryset().filter(version=version)

    @classmethod
    def get_default_plan(cls, version: ProductVersion) -> Optional[ProductPricing]:
        """Return the default pricing plan for a version."""
        return (
            cls.get_queryset()
            .filter(version=version, is_default=True)
            .first()
        )


class TenantProductRepository(BaseRepository):
    """
    Repository for TenantProduct — subscription records per tenant.
    """

    model = TenantProduct

    @classmethod
    def get_by_tenant(cls, tenant) -> QuerySet:
        """Return all product subscriptions for a given tenant."""
        return (
            cls.get_queryset()
            .filter(tenant=tenant)
            .select_related("product", "current_version", "pricing_plan")
        )

    @classmethod
    def get_active_by_tenant(cls, tenant) -> QuerySet:
        """Return only ACTIVE subscriptions for a tenant."""
        return cls.get_by_tenant(tenant).filter(
            status=TenantProductStatus.ACTIVE
        )

    @classmethod
    def get_subscription(cls, tenant, product: Product) -> Optional[TenantProduct]:
        """Fetch a specific subscription record."""
        try:
            return cls.get_queryset().select_related(
                "product", "current_version", "pricing_plan"
            ).get(tenant=tenant, product=product)
        except TenantProduct.DoesNotExist:
            return None

    @classmethod
    def is_subscribed(cls, tenant, product: Product) -> bool:
        """Check if a tenant has an active subscription to a product."""
        return cls.get_queryset().filter(
            tenant=tenant,
            product=product,
            status=TenantProductStatus.ACTIVE,
        ).exists()
