"""
KAVAN v6.0 — Marketplace Serializers
============================================================
Layer 5: DRF serializers for request validation and
response formatting.

Rules:
  - Serializers validate and transform data ONLY — no business logic.
  - Business logic belongs in services.py.
  - Read serializers (detail) may include nested representations.
  - Write serializers accept a minimal flat payload.
"""

from rest_framework import serializers

from apps.marketplace.models.product import (
    Product,
    ProductPricing,
    ProductStatus,
    ProductVersion,
    TenantProduct,
)


# ============================================================
# PRODUCT SERIALIZERS
# ============================================================

class ProductVersionListSerializer(serializers.ModelSerializer):
    """Lightweight version summary for nested product responses."""

    class Meta:
        model = ProductVersion
        fields = [
            "id",
            "version_string",
            "docker_image",
            "is_active",
            "released_at",
        ]
        read_only_fields = fields


class ProductListSerializer(serializers.ModelSerializer):
    """
    Compact product representation for marketplace catalogue listing.
    """

    latest_version = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "code",
            "name",
            "tagline",
            "category",
            "status",
            "icon_url",
            "is_featured",
            "latest_version",
        ]
        read_only_fields = fields

    def get_latest_version(self, obj: Product) -> str:
        """Return the version_string of the latest active version."""
        latest = obj.versions.filter(is_active=True).order_by("-released_at").first()
        return latest.version_string if latest else None


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Full product detail for a single product page.
    Includes nested version list.
    """

    versions = ProductVersionListSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "code",
            "name",
            "tagline",
            "description",
            "category",
            "status",
            "icon_url",
            "documentation_url",
            "support_email",
            "is_featured",
            "versions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ProductCreateSerializer(serializers.ModelSerializer):
    """
    Payload for creating a new product (platform admin).
    Validates the unique code constraint at serializer level.
    """

    class Meta:
        model = Product
        fields = [
            "code",
            "name",
            "tagline",
            "description",
            "category",
            "icon_url",
            "documentation_url",
            "support_email",
        ]

    def validate_code(self, value: str) -> str:
        """Ensure code is lowercase-hyphenated."""
        normalized = value.strip().lower().replace(" ", "-")
        return normalized


class ProductVersionCreateSerializer(serializers.ModelSerializer):
    """Payload for adding a new version to a product."""

    class Meta:
        model = ProductVersion
        fields = [
            "version_string",
            "docker_image",
            "helm_chart_ref",
            "release_notes",
            "min_memory_mb",
            "min_cpu_cores",
        ]


class ProductVersionDetailSerializer(serializers.ModelSerializer):
    """Full version details including pricing plans."""

    pricing_plans = serializers.SerializerMethodField()

    class Meta:
        model = ProductVersion
        fields = [
            "id",
            "version_string",
            "docker_image",
            "helm_chart_ref",
            "release_notes",
            "min_memory_mb",
            "min_cpu_cores",
            "is_active",
            "released_at",
            "pricing_plans",
        ]
        read_only_fields = fields

    def get_pricing_plans(self, obj: ProductVersion):
        return ProductPricingSerializer(
            obj.pricing_plans.all(), many=True
        ).data


# ============================================================
# PRICING SERIALIZERS
# ============================================================

class ProductPricingSerializer(serializers.ModelSerializer):
    """Full pricing plan representation."""

    class Meta:
        model = ProductPricing
        fields = [
            "id",
            "model",
            "price_per_unit",
            "currency",
            "billing_period_days",
            "trial_days",
            "max_seats",
            "is_default",
        ]
        read_only_fields = fields


class ProductPricingCreateSerializer(serializers.ModelSerializer):
    """Payload for creating a pricing plan."""

    class Meta:
        model = ProductPricing
        fields = [
            "model",
            "price_per_unit",
            "currency",
            "billing_period_days",
            "trial_days",
            "max_seats",
            "is_default",
        ]


# ============================================================
# TENANT PRODUCT (SUBSCRIPTION) SERIALIZERS
# ============================================================

class TenantProductSerializer(serializers.ModelSerializer):
    """
    Full subscription record representation.
    Includes nested product and version summaries.
    """

    product_name = serializers.CharField(source="product.name", read_only=True)
    product_code = serializers.CharField(source="product.code", read_only=True)
    version = serializers.CharField(
        source="current_version.version_string", read_only=True
    )
    pricing_model = serializers.CharField(
        source="pricing_plan.model", read_only=True, default=None
    )

    class Meta:
        model = TenantProduct
        fields = [
            "id",
            "product_name",
            "product_code",
            "version",
            "pricing_model",
            "status",
            "license_key",
            "seat_count",
            "trial_ends_at",
            "subscription_ends_at",
            "created_at",
        ]
        read_only_fields = fields


class ProductInstallSerializer(serializers.Serializer):
    """
    Request payload for tenant product installation.
    """

    product_code = serializers.CharField(max_length=100)
    version_string = serializers.CharField(max_length=50, required=False, allow_blank=True)
    pricing_plan_id = serializers.UUIDField(required=False, allow_null=True)


class ProductUpgradeSerializer(serializers.Serializer):
    """
    Request payload for tenant product upgrade.
    """

    target_version_string = serializers.CharField(max_length=50)