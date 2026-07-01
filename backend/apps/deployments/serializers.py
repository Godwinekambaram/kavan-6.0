"""
KAVAN v6.0 — Deployment Serializers
============================================================
Layer 6: DRF serializers for deployment API responses.
"""

from rest_framework import serializers

from apps.deployments.models import (
    DeploymentHealthCheck,
    DeploymentLog,
    DeploymentRecord,
    InfrastructureConfig,
)


class InfrastructureConfigSerializer(serializers.ModelSerializer):
    """Full infrastructure config representation."""

    class Meta:
        model = InfrastructureConfig
        fields = [
            "id",
            "provider",
            "environment",
            "region",
            "cluster_name",
            "namespace",
            "allocated_cpu_cores",
            "allocated_memory_mb",
            "allocated_storage_gb",
            "custom_domain",
            "ssl_enabled",
            "backup_enabled",
            "backup_retention_days",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class InfrastructureConfigUpdateSerializer(serializers.ModelSerializer):
    """Update payload for infrastructure config (tenant admin)."""

    class Meta:
        model = InfrastructureConfig
        fields = [
            "region",
            "allocated_cpu_cores",
            "allocated_memory_mb",
            "allocated_storage_gb",
            "custom_domain",
            "ssl_enabled",
            "backup_enabled",
            "backup_retention_days",
            "extra_env_vars",
        ]


class DeploymentLogSerializer(serializers.ModelSerializer):
    """Single deployment log entry."""

    class Meta:
        model = DeploymentLog
        fields = [
            "id",
            "level",
            "step",
            "message",
            "metadata",
            "timestamp",
        ]
        read_only_fields = fields


class DeploymentHealthCheckSerializer(serializers.ModelSerializer):
    """Health check snapshot."""

    class Meta:
        model = DeploymentHealthCheck
        fields = [
            "id",
            "status",
            "response_time_ms",
            "cpu_usage_percent",
            "memory_usage_mb",
            "error_message",
            "checked_at",
        ]
        read_only_fields = fields


class DeploymentRecordListSerializer(serializers.ModelSerializer):
    """Compact deployment record for list views."""

    product_name = serializers.CharField(
        source="tenant_product.product.name", read_only=True
    )
    duration_seconds = serializers.SerializerMethodField()

    class Meta:
        model = DeploymentRecord
        fields = [
            "id",
            "product_name",
            "deployment_type",
            "status",
            "from_version",
            "to_version",
            "service_url",
            "queued_at",
            "started_at",
            "completed_at",
            "duration_seconds",
            "retry_count",
        ]
        read_only_fields = fields

    def get_duration_seconds(self, obj: DeploymentRecord):
        return obj.duration_seconds


class DeploymentRecordDetailSerializer(serializers.ModelSerializer):
    """Full deployment record with logs and latest health check."""

    product_name = serializers.CharField(
        source="tenant_product.product.name", read_only=True
    )
    logs = DeploymentLogSerializer(many=True, read_only=True)
    latest_health = serializers.SerializerMethodField()
    duration_seconds = serializers.SerializerMethodField()
    infra_config = InfrastructureConfigSerializer(read_only=True)

    class Meta:
        model = DeploymentRecord
        fields = [
            "id",
            "product_name",
            "deployment_type",
            "status",
            "from_version",
            "to_version",
            "container_id",
            "service_url",
            "internal_ip",
            "port",
            "infra_config",
            "queued_at",
            "started_at",
            "completed_at",
            "duration_seconds",
            "error_message",
            "error_code",
            "retry_count",
            "max_retries",
            "celery_task_id",
            "logs",
            "latest_health",
        ]
        read_only_fields = fields

    def get_duration_seconds(self, obj: DeploymentRecord):
        return obj.duration_seconds

    def get_latest_health(self, obj: DeploymentRecord):
        latest = obj.health_checks.order_by("-checked_at").first()
        if latest:
            return DeploymentHealthCheckSerializer(latest).data
        return None


class RollbackSerializer(serializers.Serializer):
    """Request payload for a manual rollback."""

    target_version_string = serializers.CharField(max_length=50)
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)
