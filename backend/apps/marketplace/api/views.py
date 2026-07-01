"""
KAVAN v6.0 — Marketplace API Views
============================================================
Layer 5: DRF view controllers for the marketplace.

Two distinct API surfaces:
  1. Platform Admin APIs  — /api/v1/marketplace/admin/
     → Requires platform:manage_products permission
     → Create, publish, archive products; manage versions & pricing

  2. Tenant Marketplace APIs — /api/v1/marketplace/
     → Requires tenant-level authentication
     → Browse catalogue, install, upgrade, uninstall products

Rules:
  - Views contain ZERO business logic.
  - All operations are delegated to service classes.
  - All responses use StandardResponse helpers from BaseAPIView.
"""

import logging

from django.utils.decorators import method_decorator

from apps.marketplace.serializers import (
    ProductCreateSerializer,
    ProductDetailSerializer,
    ProductInstallSerializer,
    ProductListSerializer,
    ProductPricingCreateSerializer,
    ProductUpgradeSerializer,
    ProductVersionCreateSerializer,
    ProductVersionDetailSerializer,
    TenantProductSerializer,
)
from apps.marketplace.services import (
    MarketplaceService,
    ProductCatalogueService,
    ProductNotFoundException,
    ProductAlreadyInstalledException,
    ProductNotAvailableException,
    SubscriptionNotFoundException,
)
from apps.rbac.decorators import platform_permission, tenant_permission
from common.exceptions.base import ValidationException
from common.views.base import BaseAPIView

logger = logging.getLogger("kavan.marketplace.views")


# ============================================================
# PLATFORM ADMIN VIEWS
# ============================================================

class AdminProductListCreateView(BaseAPIView):
    """
    GET  /api/v1/marketplace/admin/products/
        List all products (any status) for platform admin.

    POST /api/v1/marketplace/admin/products/
        Create a new product in DRAFT status.

    Permissions: platform:manage_products
    """

    @method_decorator(platform_permission("platform:manage_products"))
    def get(self, request):
        from apps.marketplace.repositories import ProductRepository
        products = ProductRepository.get_queryset().order_by("-created_at")
        serializer = ProductListSerializer(products, many=True)
        return self.success(
            data={"products": serializer.data, "count": products.count()},
            message="Product catalogue retrieved.",
        )

    @method_decorator(platform_permission("platform:manage_products"))
    def post(self, request):
        serializer = ProductCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error(
                message="Invalid product data.",
                errors=serializer.errors,
            )

        try:
            product = ProductCatalogueService.create_product(**serializer.validated_data)
        except ValidationException as exc:
            return self.error(message=str(exc.message), status=409)

        return self.created(
            data=ProductDetailSerializer(product).data,
            message="Product created successfully.",
        )


class AdminProductDetailView(BaseAPIView):
    """
    GET   /api/v1/marketplace/admin/products/<code>/
          Retrieve full product detail.

    PATCH /api/v1/marketplace/admin/products/<code>/publish/
    PATCH /api/v1/marketplace/admin/products/<code>/archive/

    Permissions: platform:manage_products
    """

    @method_decorator(platform_permission("platform:manage_products"))
    def get(self, request, code):
        from apps.marketplace.repositories import ProductRepository
        product = ProductRepository.get_by_code(code)
        if not product:
            return self.not_found(f"Product '{code}' not found.")

        return self.success(
            data=ProductDetailSerializer(product).data,
            message="Product retrieved.",
        )


class AdminProductPublishView(BaseAPIView):
    """
    POST /api/v1/marketplace/admin/products/<product_id>/publish/
    Publish a product to the marketplace.
    """

    @method_decorator(platform_permission("platform:manage_products"))
    def post(self, request, product_id):
        try:
            product = ProductCatalogueService.publish_product(product_id)
        except ProductNotFoundException:
            return self.not_found("Product not found.")
        except ValidationException as exc:
            return self.error(message=str(exc.message))

        return self.success(
            data=ProductDetailSerializer(product).data,
            message="Product published successfully.",
        )


class AdminProductArchiveView(BaseAPIView):
    """
    POST /api/v1/marketplace/admin/products/<product_id>/archive/
    Archive a product.
    """

    @method_decorator(platform_permission("platform:manage_products"))
    def post(self, request, product_id):
        try:
            product = ProductCatalogueService.archive_product(product_id)
        except ProductNotFoundException:
            return self.not_found("Product not found.")

        return self.success(
            data=ProductDetailSerializer(product).data,
            message="Product archived.",
        )


class AdminProductVersionListCreateView(BaseAPIView):
    """
    GET  /api/v1/marketplace/admin/products/<product_id>/versions/
         List all versions for a product.

    POST /api/v1/marketplace/admin/products/<product_id>/versions/
         Add a new version to an existing product.
    """

    @method_decorator(platform_permission("platform:manage_products"))
    def get(self, request, product_id):
        from apps.marketplace.repositories import (
            ProductRepository,
            ProductVersionRepository,
        )
        product = ProductRepository.get_by_id(product_id)
        if not product:
            return self.not_found("Product not found.")

        versions = ProductVersionRepository.get_active_versions(product)
        serializer = ProductVersionDetailSerializer(versions, many=True)
        return self.success(
            data={"versions": serializer.data, "count": versions.count()},
            message="Product versions retrieved.",
        )

    @method_decorator(platform_permission("platform:manage_products"))
    def post(self, request, product_id):
        serializer = ProductVersionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error(
                message="Invalid version data.",
                errors=serializer.errors,
            )

        try:
            version = ProductCatalogueService.add_product_version(
                product_id=product_id,
                **serializer.validated_data,
            )
        except (ProductNotFoundException, ValidationException) as exc:
            msg = getattr(exc, "message", str(exc))
            return self.error(message=msg)

        return self.created(
            data=ProductVersionDetailSerializer(version).data,
            message="Product version added.",
        )


class AdminProductPricingView(BaseAPIView):
    """
    POST /api/v1/marketplace/admin/versions/<version_id>/pricing/
         Set a pricing plan for a product version.
    """

    @method_decorator(platform_permission("platform:manage_products"))
    def post(self, request, version_id):
        serializer = ProductPricingCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error(
                message="Invalid pricing data.",
                errors=serializer.errors,
            )

        try:
            pricing = ProductCatalogueService.set_pricing(
                version_id=version_id,
                **serializer.validated_data,
            )
        except ValidationException as exc:
            return self.error(message=str(exc.message))

        from apps.marketplace.serializers import ProductPricingSerializer
        return self.created(
            data=ProductPricingSerializer(pricing).data,
            message="Pricing plan set.",
        )


# ============================================================
# TENANT MARKETPLACE VIEWS
# ============================================================

class MarketplaceCatalogueView(BaseAPIView):
    """
    GET /api/v1/marketplace/catalogue/
    Browse all published products.

    Optional query params:
      ?category=CRM
    """

    @method_decorator(tenant_permission("marketplace:view"))
    def get(self, request):
        category = request.query_params.get("category")
        products = MarketplaceService.list_available_products(category=category)
        serializer = ProductListSerializer(products, many=True)
        return self.success(
            data={"products": serializer.data, "count": len(products)},
            message="Marketplace catalogue retrieved.",
        )


class MarketplaceProductDetailView(BaseAPIView):
    """
    GET /api/v1/marketplace/catalogue/<code>/
    View a single published product and its versions.
    """

    @method_decorator(tenant_permission("marketplace:view"))
    def get(self, request, code):
        try:
            product = MarketplaceService.get_product_detail(code)
        except ProductNotFoundException:
            return self.not_found(f"Product '{code}' not found.")
        except ProductNotAvailableException:
            return self.not_found("This product is not currently available.")

        return self.success(
            data=ProductDetailSerializer(product).data,
            message="Product details retrieved.",
        )


class TenantInstalledProductsView(BaseAPIView):
    """
    GET /api/v1/marketplace/installed/
    List all active product subscriptions for the current tenant.
    """

    @method_decorator(tenant_permission("marketplace:view"))
    def get(self, request):
        tenant = getattr(request, "tenant", None)
        subscriptions = MarketplaceService.get_tenant_subscriptions(tenant)
        serializer = TenantProductSerializer(subscriptions, many=True)
        return self.success(
            data={"subscriptions": serializer.data, "count": len(subscriptions)},
            message="Installed products retrieved.",
        )


class TenantProductInstallView(BaseAPIView):
    """
    POST /api/v1/marketplace/install/
    Install (subscribe) a product to the current tenant.

    Body:
      {
        "product_code": "crm-pro",
        "version_string": "v1.2.0",    // optional
        "pricing_plan_id": "<uuid>"    // optional
      }
    """

    @method_decorator(tenant_permission("marketplace:install"))
    def post(self, request):
        serializer = ProductInstallSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error(
                message="Invalid installation request.",
                errors=serializer.errors,
            )

        tenant = getattr(request, "tenant", None)

        try:
            subscription = MarketplaceService.install_product(
                tenant=tenant,
                product_code=serializer.validated_data["product_code"],
                version_string=serializer.validated_data.get("version_string"),
                pricing_plan_id=serializer.validated_data.get("pricing_plan_id"),
                installed_by=request.user,
            )
        except ProductNotFoundException:
            return self.not_found("Product not found.")
        except ProductNotAvailableException:
            return self.error(message="This product is not available for installation.", status=403)
        except ProductAlreadyInstalledException:
            return self.error(message="This product is already installed.", status=409)
        except ValidationException as exc:
            return self.error(message=str(exc.message))

        return self.created(
            data=TenantProductSerializer(subscription).data,
            message="Product installation initiated. Deployment is in progress.",
        )


class TenantProductUpgradeView(BaseAPIView):
    """
    POST /api/v1/marketplace/products/<code>/upgrade/
    Upgrade a tenant's installed product to a new version.

    Body:
      { "target_version_string": "v2.0.0" }
    """

    @method_decorator(tenant_permission("marketplace:install"))
    def post(self, request, code):
        serializer = ProductUpgradeSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error(
                message="Invalid upgrade request.",
                errors=serializer.errors,
            )

        tenant = getattr(request, "tenant", None)

        try:
            subscription = MarketplaceService.upgrade_product(
                tenant=tenant,
                product_code=code,
                target_version_string=serializer.validated_data["target_version_string"],
            )
        except ProductNotFoundException:
            return self.not_found("Product not found.")
        except SubscriptionNotFoundException:
            return self.not_found("No active subscription found for this product.")
        except ValidationException as exc:
            return self.error(message=str(exc.message))

        return self.success(
            data=TenantProductSerializer(subscription).data,
            message="Product upgrade initiated.",
        )


class TenantProductUninstallView(BaseAPIView):
    """
    DELETE /api/v1/marketplace/products/<code>/uninstall/
    Cancel and uninstall a product from the current tenant.
    """

    @method_decorator(tenant_permission("marketplace:install"))
    def delete(self, request, code):
        tenant = getattr(request, "tenant", None)

        try:
            subscription = MarketplaceService.uninstall_product(
                tenant=tenant,
                product_code=code,
            )
        except ProductNotFoundException:
            return self.not_found("Product not found.")
        except SubscriptionNotFoundException:
            return self.not_found("No subscription found for this product.")

        return self.success(
            data=TenantProductSerializer(subscription).data,
            message="Product uninstalled successfully.",
        )
