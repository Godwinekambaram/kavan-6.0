"""
KAVAN v6.0 — Marketplace URL Configuration
============================================================
Layer 5: Marketplace & Product Management API Routes

Platform Admin Routes  → /api/v1/marketplace/admin/...
Tenant Routes          → /api/v1/marketplace/...
"""

from django.urls import path

from apps.marketplace.api.views import (
    # Platform Admin
    AdminProductArchiveView,
    AdminProductDetailView,
    AdminProductListCreateView,
    AdminProductPricingView,
    AdminProductPublishView,
    AdminProductVersionListCreateView,
    # Tenant-facing
    MarketplaceCatalogueView,
    MarketplaceProductDetailView,
    TenantInstalledProductsView,
    TenantProductInstallView,
    TenantProductUninstallView,
    TenantProductUpgradeView,
)

app_name = "marketplace"

urlpatterns = [
    # --------------------------------------------------------
    # PLATFORM ADMIN — Product Management
    # --------------------------------------------------------

    # POST   /api/v1/marketplace/admin/products/
    # GET    /api/v1/marketplace/admin/products/
    path(
        "admin/products/",
        AdminProductListCreateView.as_view(),
        name="admin-product-list-create",
    ),

    # GET    /api/v1/marketplace/admin/products/<code>/
    path(
        "admin/products/<str:code>/",
        AdminProductDetailView.as_view(),
        name="admin-product-detail",
    ),

    # POST   /api/v1/marketplace/admin/products/<product_id>/publish/
    path(
        "admin/products/<uuid:product_id>/publish/",
        AdminProductPublishView.as_view(),
        name="admin-product-publish",
    ),

    # POST   /api/v1/marketplace/admin/products/<product_id>/archive/
    path(
        "admin/products/<uuid:product_id>/archive/",
        AdminProductArchiveView.as_view(),
        name="admin-product-archive",
    ),

    # GET    /api/v1/marketplace/admin/products/<product_id>/versions/
    # POST   /api/v1/marketplace/admin/products/<product_id>/versions/
    path(
        "admin/products/<uuid:product_id>/versions/",
        AdminProductVersionListCreateView.as_view(),
        name="admin-product-versions",
    ),

    # POST   /api/v1/marketplace/admin/versions/<version_id>/pricing/
    path(
        "admin/versions/<uuid:version_id>/pricing/",
        AdminProductPricingView.as_view(),
        name="admin-version-pricing",
    ),

    # --------------------------------------------------------
    # TENANT — Marketplace Browse & Subscription
    # --------------------------------------------------------

    # GET    /api/v1/marketplace/catalogue/
    path(
        "catalogue/",
        MarketplaceCatalogueView.as_view(),
        name="catalogue",
    ),

    # GET    /api/v1/marketplace/catalogue/<code>/
    path(
        "catalogue/<str:code>/",
        MarketplaceProductDetailView.as_view(),
        name="product-detail",
    ),

    # GET    /api/v1/marketplace/installed/
    path(
        "installed/",
        TenantInstalledProductsView.as_view(),
        name="installed-products",
    ),

    # POST   /api/v1/marketplace/install/
    path(
        "install/",
        TenantProductInstallView.as_view(),
        name="product-install",
    ),

    # POST   /api/v1/marketplace/products/<code>/upgrade/
    path(
        "products/<str:code>/upgrade/",
        TenantProductUpgradeView.as_view(),
        name="product-upgrade",
    ),

    # DELETE /api/v1/marketplace/products/<code>/uninstall/
    path(
        "products/<str:code>/uninstall/",
        TenantProductUninstallView.as_view(),
        name="product-uninstall",
    ),
]
