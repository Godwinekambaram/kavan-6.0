"""
KAVAN v6.0 — Deployment Repository
============================================================
Layer 6: Data access abstraction for deployment models.

Rules:
  - No business logic — pure data access.
  - DeploymentLogRepository only inserts, never updates.
  - All query methods return typed results.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from django.db.models import QuerySet

from apps.deployments.models import (
    DeploymentHealthCheck,
    DeploymentLog,
    DeploymentRecord,
    DeploymentStatus,
    HealthStatus,
    InfrastructureConfig,
)
from common.repositories.base_repository import BaseRepository

logger = logging.getLogger("kavan.deployments.repositories")


class DeploymentRepository(BaseRepository):
    """
    Repository for DeploymentRecord — the deployment state machine.
    """

    model = DeploymentRecord

    @classmethod
    def get_by_tenant_product(cls, tenant_product_id: str) -> QuerySet:
        """Return all deployments for a given TenantProduct subscription."""
        return cls.get_queryset().filter(
            tenant_product_id=tenant_product_id
        ).select_related("infra_config").order_by("-queued_at")

    @classmethod
    def get_active_deployment(cls, tenant_product_id: str) -> Optional[DeploymentRecord]:
        """Return the currently RUNNING deployment for a subscription."""
        return (
            cls.get_queryset()
            .filter(
                tenant_product_id=tenant_product_id,
                status=DeploymentStatus.RUNNING,
            )
            .first()
        )

    @classmethod
    def get_latest(cls, tenant_product_id: str) -> Optional[DeploymentRecord]:
        """Return the most recent deployment record for a subscription."""
        return (
            cls.get_queryset()
            .filter(tenant_product_id=tenant_product_id)
            .order_by("-queued_at")
            .first()
        )

    @classmethod
    def get_pending(cls) -> QuerySet:
        """Return all QUEUED deployments awaiting execution."""
        return cls.get_queryset().filter(
            status=DeploymentStatus.QUEUED
        ).order_by("queued_at")

    @classmethod
    def get_failed_with_retries(cls) -> QuerySet:
        """Return FAILED deployments that still have retry budget."""
        from django.db.models import F
        return cls.get_queryset().filter(
            status=DeploymentStatus.FAILED,
            retry_count__lt=F("max_retries"),
        )

    @classmethod
    def transition_status(
        cls,
        deployment: DeploymentRecord,
        new_status: str,
        **extra_fields,
    ) -> DeploymentRecord:
        """
        Atomically update the deployment status and optional extra fields.
        Sets started_at/completed_at timestamps automatically.
        """
        now = datetime.now(tz=timezone.utc)
        update_fields = {"status": new_status, "updated_at": now}

        if new_status == DeploymentStatus.PROVISIONING and not deployment.started_at:
            update_fields["started_at"] = now

        if new_status in (
            DeploymentStatus.RUNNING,
            DeploymentStatus.FAILED,
            DeploymentStatus.DECOMMISSIONED,
            DeploymentStatus.STOPPED,
        ):
            update_fields["completed_at"] = now

        update_fields.update(extra_fields)
        return cls.update(deployment, **update_fields)


class InfrastructureConfigRepository(BaseRepository):
    """
    Repository for InfrastructureConfig — per-tenant infra spec.
    """

    model = InfrastructureConfig

    @classmethod
    def get_by_tenant(cls, tenant) -> Optional[InfrastructureConfig]:
        """Retrieve the infrastructure configuration for a tenant."""
        try:
            return cls.get_queryset().get(tenant=tenant)
        except InfrastructureConfig.DoesNotExist:
            return None

    @classmethod
    def get_or_create_default(cls, tenant) -> InfrastructureConfig:
        """
        Return existing config or create a default KAVAN Cloud config
        if none exists for this tenant.
        """
        config = cls.get_by_tenant(tenant)
        if config:
            return config

        return cls.create(tenant=tenant)


class DeploymentLogRepository:
    """
    Append-only repository for DeploymentLog entries.
    No BaseRepository inheritance — inserts only, no updates.
    """

    @staticmethod
    def append(
        deployment: DeploymentRecord,
        message: str,
        level: str = "INFO",
        step: str = "",
        metadata: dict = None,
    ) -> DeploymentLog:
        """
        Append a new log entry to a deployment.

        Args:
            deployment: Parent DeploymentRecord.
            message:    Human-readable log message.
            level:      LogLevel choice (DEBUG/INFO/WARNING/ERROR/CRITICAL).
            step:       Named deployment step for filtering.
            metadata:   Structured context dict.

        Returns:
            Newly created DeploymentLog instance.
        """
        return DeploymentLog.objects.create(
            deployment=deployment,
            level=level,
            step=step,
            message=message,
            metadata=metadata or {},
        )

    @staticmethod
    def get_for_deployment(
        deployment: DeploymentRecord,
        level: str = None,
    ) -> QuerySet:
        """
        Return all log entries for a deployment.
        Optionally filter by level.
        """
        qs = DeploymentLog.objects.filter(deployment=deployment)
        if level:
            qs = qs.filter(level=level)
        return qs.order_by("timestamp")


class DeploymentHealthCheckRepository(BaseRepository):
    """
    Repository for DeploymentHealthCheck records.
    """

    model = DeploymentHealthCheck

    @classmethod
    def get_latest(cls, deployment: DeploymentRecord) -> Optional[DeploymentHealthCheck]:
        """Return the most recent health check for a deployment."""
        return (
            cls.get_queryset()
            .filter(deployment=deployment)
            .order_by("-checked_at")
            .first()
        )

    @classmethod
    def get_history(cls, deployment: DeploymentRecord, limit: int = 100) -> QuerySet:
        """Return the health check history for a deployment."""
        return (
            cls.get_queryset()
            .filter(deployment=deployment)
            .order_by("-checked_at")[:limit]
        )

    @classmethod
    def record_check(
        cls,
        deployment: DeploymentRecord,
        status: str,
        response_time_ms: int = None,
        cpu_usage_percent: float = None,
        memory_usage_mb: int = None,
        error_message: str = "",
    ) -> DeploymentHealthCheck:
        """Insert a new health check snapshot."""
        return cls.create(
            deployment=deployment,
            status=status,
            response_time_ms=response_time_ms,
            cpu_usage_percent=cpu_usage_percent,
            memory_usage_mb=memory_usage_mb,
            error_message=error_message,
        )
