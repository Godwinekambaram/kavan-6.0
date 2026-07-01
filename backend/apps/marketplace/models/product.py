"""
KAVAN v6.0 — Marketplace Models
============================================================
Layer 5: Product & Marketplace Data Models

Models:
  - Product          : Global product definition (platform-level)
  - ProductVersion   : Immutable versioned release of a product
  - ProductPricing   : Pricing plan attached to a product version
  - TenantProduct    : Records a tenant's subscription to a product
  - ProductDeployment: Tracks the provisioning lifecycle per install

Rules:
  - All models extend BaseModel (UUID PK, timestamps, soft delete)
  - Products are platform-owned; tenants subscribe via TenantProduct
  - Deployment records are created by Layer 6 (DeploymentEngine)
  - Status fields use TextChoices for type safety
"""

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models.base_model import BaseModel


# ============================================================
# ENUMERATIONS
# ============================================================

class ProductStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft")
    PUBLISHED = "PUBLISHED", _("Published")
    DEPRECATED = "DEPRECATED", _("Deprecated")
    ARCHIVED = "ARCHIVED", _("Archived")


class ProductCategory(models.TextChoices):
    CRM = "CRM", _("Customer Relationship Management")
    ERP = "ERP", _("Enterprise Resource Planning")
    HRM = "HRM", _("Human Resource Management")
    ANALYTICS = "ANALYTICS", _("Analytics & Reporting")
    COMMUNICATION = "COMMUNICATION", _("Communication & Messaging")
    SECURITY = "SECURITY", _("Security & Compliance")
    FINANCE = "FINANCE", _("Finance & Billing")
    OTHER = "OTHER", _("Other")


class DeploymentMode(models.TextChoices):
    CLOUD = "CLOUD", _("Managed Cloud")
    HYBRID = "HYBRID", _("Hybrid Deployment")
    ON_PREMISE = "ON_PREMISE", _("On-Premise Self-Hosted")


class PricingModel(models.TextChoices):
    FREE = "FREE", _("Free Tier")
    FLAT = "FLAT", _("Flat Monthly Fee")
    PER_SEAT = "PER_SEAT", _("Per Seat / User")
    USAGE_BASED = "USAGE_BASED", _("Usage-Based")
    ENTERPRISE = "ENTERPRISE", _("Enterprise Contract")


class TenantProductStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending Activation")
    ACTIVE = "ACTIVE", _("Active")
    SUSPENDED = "SUSPENDED", _("Suspended")
    CANCELLED = "CANCELLED", _("Cancelled")
    EXPIRED = "EXPIRED", _("Expired")


# ============================================================
# PRODUCT
# ============================================================

class Product(BaseModel):
    """
    Platform-level product definition.
    Created and managed exclusively by Super Admins (platform:create_product).

    Each product may have multiple versioned releases (ProductVersion).
    Tenants subscribe to a product via TenantProduct.
    """

    code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique machine-readable identifier (e.g., 'crm-pro', 'erp-lite').",
    )
    name = models.CharField(max_length=255)
    tagline = models.CharField(
        max_length=512,
        blank=True,
        help_text="Short marketing description shown in the marketplace.",
    )
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=50,
        choices=ProductCategory.choices,
        default=ProductCategory.OTHER,
        db_index=True,
    )
    status = models.CharField(
        max_length=32,
        choices=ProductStatus.choices,
        default=ProductStatus.DRAFT,
        db_index=True,
    )
    icon_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL to product icon/logo displayed in the marketplace.",
    )
    documentation_url = models.URLField(
        blank=True,
        null=True,
        help_text="Link to public product documentation.",
    )
    support_email = models.EmailField(blank=True, null=True)
    is_featured = models.BooleanField(
        default=False,
        help_text="If True, product is highlighted on the marketplace homepage.",
    )

    class Meta(BaseModel.Meta):
        db_table = "marketplace_products"
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["-is_featured", "name"]

    def __str__(self) -> str:
        return f"{self.name} [{self.code}] ({self.status})"

    def publish(self) -> None:
        """Mark the product as published (visible in marketplace)."""
        self.status = ProductStatus.PUBLISHED
        self.save(update_fields=["status", "updated_at"])

    def archive(self) -> None:
        """Retire the product from the marketplace."""
        self.status = ProductStatus.ARCHIVED
        self.save(update_fields=["status", "updated_at"])


# ============================================================
# PRODUCT VERSION
# ============================================================

class ProductVersion(BaseModel):
    """
    Immutable versioned release of a Product.

    Each version points to a specific Docker image and carries
    a changelog. Once published, versions are never mutated —
    tenants always deploy against a locked version reference.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version_string = models.CharField(
        max_length=50,
        help_text="Semantic version string (e.g., 'v1.2.0').",
    )
    release_notes = models.TextField(
        blank=True,
        help_text="Human-readable changelog for this release.",
    )
    docker_image = models.CharField(
        max_length=512,
        blank=True,
        help_text="Fully-qualified container image reference (e.g., 'registry.kavan.io/crm:v1.2.0').",
    )
    helm_chart_ref = models.CharField(
        max_length=512,
        blank=True,
        help_text="Optional Helm chart repository reference for Kubernetes deployments.",
    )
    min_memory_mb = models.PositiveIntegerField(
        default=512,
        help_text="Minimum RAM (MB) required to run this version.",
    )
    min_cpu_cores = models.PositiveSmallIntegerField(
        default=1,
        help_text="Minimum CPU cores required to run this version.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="If False, this version is EOL and cannot be newly deployed.",
    )
    released_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when this version was officially released.",
    )

    class Meta(BaseModel.Meta):
        db_table = "marketplace_product_versions"
        verbose_name = _("Product Version")
        verbose_name_plural = _("Product Versions")
        unique_together = ("product", "version_string")
        ordering = ["-released_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.product.name} {self.version_string}"


# ============================================================
# PRODUCT PRICING
# ============================================================

class ProductPricing(BaseModel):
    """
    Pricing plan for a specific ProductVersion.

    A single version may carry multiple pricing tiers
    (e.g., FREE + PER_SEAT). The active plan is resolved
    at subscription time by the MarketplaceService.
    """

    version = models.ForeignKey(
        ProductVersion,
        on_delete=models.CASCADE,
        related_name="pricing_plans",
    )
    model = models.CharField(
        max_length=32,
        choices=PricingModel.choices,
        default=PricingModel.FLAT,
    )
    price_per_unit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        help_text="Price per billing unit (month/seat/request). 0 for FREE tier.",
    )
    currency = models.CharField(max_length=3, default="USD")
    billing_period_days = models.PositiveIntegerField(
        default=30,
        help_text="Billing cycle length in days.",
    )
    trial_days = models.PositiveIntegerField(
        default=0,
        help_text="Free trial period before billing commences.",
    )
    max_seats = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of seats (NULL = unlimited).",
    )
    is_default = models.BooleanField(
        default=False,
        help_text="True if this is the default plan shown during install flow.",
    )

    class Meta(BaseModel.Meta):
        db_table = "marketplace_product_pricing"
        verbose_name = _("Product Pricing")
        verbose_name_plural = _("Product Pricing Plans")

    def __str__(self) -> str:
        return f"{self.version} — {self.model} @ {self.price_per_unit} {self.currency}"


# ============================================================
# TENANT PRODUCT (SUBSCRIPTION)
# ============================================================

class TenantProduct(BaseModel):
    """
    Associates a Tenant with a Product subscription.

    Represents an installed/subscribed product for a tenant.
    Contains billing metadata, active version reference,
    and lifecycle status.
    """

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="subscribed_products",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="tenant_subscriptions",
    )
    current_version = models.ForeignKey(
        ProductVersion,
        on_delete=models.PROTECT,
        related_name="active_subscriptions",
        help_text="The currently active product version for this tenant.",
    )
    pricing_plan = models.ForeignKey(
        ProductPricing,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscriptions",
    )
    status = models.CharField(
        max_length=32,
        choices=TenantProductStatus.choices,
        default=TenantProductStatus.PENDING,
        db_index=True,
    )
    license_key = models.CharField(
        max_length=512,
        blank=True,
        unique=True,
        help_text="Platform-issued license key for this subscription.",
    )
    seat_count = models.PositiveIntegerField(
        default=1,
        help_text="Number of licensed seats for PER_SEAT pricing.",
    )
    trial_ends_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Expiry of the free trial period (NULL = no trial).",
    )
    subscription_ends_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Subscription renewal or expiry timestamp.",
    )
    installed_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="installed_products",
    )

    class Meta(BaseModel.Meta):
        db_table = "marketplace_tenant_products"
        verbose_name = _("Tenant Product Subscription")
        verbose_name_plural = _("Tenant Product Subscriptions")
        unique_together = ("tenant", "product")

    def __str__(self) -> str:
        return f"{self.tenant} → {self.product.name} ({self.status})"

    def activate(self) -> None:
        """Mark subscription as active."""
        self.status = TenantProductStatus.ACTIVE
        self.save(update_fields=["status", "updated_at"])

    def suspend(self) -> None:
        """Suspend the subscription (billing overdue, admin action)."""
        self.status = TenantProductStatus.SUSPENDED
        self.save(update_fields=["status", "updated_at"])

    def cancel(self) -> None:
        """Permanently cancel the subscription."""
        self.status = TenantProductStatus.CANCELLED
        self.save(update_fields=["status", "updated_at"])
