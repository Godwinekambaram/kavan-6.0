"""
KAVAN v6.0 — Deployment Models
============================================================
Layer 6: Deployment & Provisioning Engine Data Models

Models:
  - DeploymentRecord   : Tracks a single deployment lifecycle event
  - DeploymentLog      : Append-only structured log entries per deployment
  - DeploymentHealthCheck: Periodic health snapshot of a running deployment
  - InfrastructureConfig: Per-tenant infrastructure provisioning spec

Rules:
  - All models extend BaseModel (UUID PK, timestamps, soft delete).
  - DeploymentRecord is the canonical state machine for a provisioning op.
  - DeploymentLog is APPEND-ONLY (no updates permitted).
  - Status transitions are enforced by the DeploymentService.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models.base_model import BaseModel


# ============================================================
# ENUMERATIONS
# ============================================================

class DeploymentStatus(models.TextChoices):
    QUEUED = "QUEUED", _("Queued")
    PROVISIONING = "PROVISIONING", _("Provisioning Infrastructure")
    PULLING_IMAGE = "PULLING_IMAGE", _("Pulling Container Image")
    CONFIGURING = "CONFIGURING", _("Configuring Environment")
    STARTING = "STARTING", _("Starting Services")
    RUNNING = "RUNNING", _("Running")
    UPGRADING = "UPGRADING", _("Upgrading")
    ROLLBACK = "ROLLBACK", _("Rolling Back")
    STOPPING = "STOPPING", _("Stopping")
    STOPPED = "STOPPED", _("Stopped")
    DECOMMISSIONED = "DECOMMISSIONED", _("Decommissioned")
    FAILED = "FAILED", _("Failed")
    DEGRADED = "DEGRADED", _("Degraded")


class DeploymentType(models.TextChoices):
    PROVISION = "PROVISION", _("Initial Provisioning")
    UPGRADE = "UPGRADE", _("Version Upgrade")
    ROLLBACK = "ROLLBACK", _("Version Rollback")
    RESTART = "RESTART", _("Service Restart")
    DECOMMISSION = "DECOMMISSION", _("Decommission / Teardown")
    HEALTH_REPAIR = "HEALTH_REPAIR", _("Automated Health Repair")


class DeploymentEnvironment(models.TextChoices):
    DEVELOPMENT = "DEVELOPMENT", _("Development")
    STAGING = "STAGING", _("Staging")
    PRODUCTION = "PRODUCTION", _("Production")


class InfrastructureProvider(models.TextChoices):
    KAVAN_CLOUD = "KAVAN_CLOUD", _("KAVAN Managed Cloud")
    AWS = "AWS", _("Amazon Web Services")
    GCP = "GCP", _("Google Cloud Platform")
    AZURE = "AZURE", _("Microsoft Azure")
    ON_PREMISE = "ON_PREMISE", _("On-Premise / Self-Hosted")
    DOCKER_LOCAL = "DOCKER_LOCAL", _("Local Docker (Development)")


class LogLevel(models.TextChoices):
    DEBUG = "DEBUG", _("Debug")
    INFO = "INFO", _("Info")
    WARNING = "WARNING", _("Warning")
    ERROR = "ERROR", _("Error")
    CRITICAL = "CRITICAL", _("Critical")


class HealthStatus(models.TextChoices):
    HEALTHY = "HEALTHY", _("Healthy")
    DEGRADED = "DEGRADED", _("Degraded")
    UNHEALTHY = "UNHEALTHY", _("Unhealthy")
    UNKNOWN = "UNKNOWN", _("Unknown")


# ============================================================
# INFRASTRUCTURE CONFIG
# ============================================================

class InfrastructureConfig(BaseModel):
    """
    Per-tenant infrastructure provisioning specification.

    Defines WHERE and HOW a product will be deployed for a tenant.
    Created once during onboarding and reused for all subsequent
    deployments unless the tenant changes their infrastructure plan.
    """

    tenant = models.OneToOneField(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="infra_config",
    )
    provider = models.CharField(
        max_length=32,
        choices=InfrastructureProvider.choices,
        default=InfrastructureProvider.KAVAN_CLOUD,
    )
    environment = models.CharField(
        max_length=32,
        choices=DeploymentEnvironment.choices,
        default=DeploymentEnvironment.PRODUCTION,
    )
    region = models.CharField(
        max_length=100,
        default="us-east-1",
        help_text="Cloud region or data centre location.",
    )
    cluster_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Kubernetes cluster name (if K8s deployment).",
    )
    namespace = models.CharField(
        max_length=255,
        blank=True,
        help_text="K8s namespace or Docker network for isolation.",
    )
    allocated_cpu_cores = models.PositiveSmallIntegerField(
        default=2,
        help_text="vCPU cores allocated to this tenant's deployments.",
    )
    allocated_memory_mb = models.PositiveIntegerField(
        default=2048,
        help_text="RAM (MB) allocated to this tenant's deployments.",
    )
    allocated_storage_gb = models.PositiveIntegerField(
        default=20,
        help_text="Persistent storage (GB) allocated.",
    )
    custom_domain = models.CharField(
        max_length=255,
        blank=True,
        help_text="Custom domain mapped to this tenant's deployment.",
    )
    ssl_enabled = models.BooleanField(
        default=True,
        help_text="Whether SSL/TLS is enabled for this tenant's endpoints.",
    )
    backup_enabled = models.BooleanField(
        default=True,
        help_text="Whether automated backups are enabled.",
    )
    backup_retention_days = models.PositiveSmallIntegerField(
        default=30,
        help_text="Number of days to retain automated backups.",
    )
    extra_env_vars = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional environment variables injected into deployments.",
    )

    class Meta(BaseModel.Meta):
        db_table = "deployments_infra_config"
        verbose_name = _("Infrastructure Config")
        verbose_name_plural = _("Infrastructure Configs")

    def __str__(self) -> str:
        return f"InfraConfig[{self.tenant}] @ {self.provider}/{self.region}"


# ============================================================
# DEPLOYMENT RECORD
# ============================================================

class DeploymentRecord(BaseModel):
    """
    Canonical state machine record for a single deployment operation.

    Each install/upgrade/rollback/decommission operation creates
    exactly one DeploymentRecord. The status field tracks the
    current lifecycle stage.

    Transition rules (enforced by DeploymentService):
      QUEUED → PROVISIONING → PULLING_IMAGE → CONFIGURING → STARTING → RUNNING
      RUNNING → UPGRADING → RUNNING
      RUNNING → ROLLBACK → RUNNING
      RUNNING → STOPPING → STOPPED → DECOMMISSIONED
      Any → FAILED
    """

    # ---- Relationships ----
    tenant_product = models.ForeignKey(
        "marketplace.TenantProduct",
        on_delete=models.CASCADE,
        related_name="deployments",
        help_text="The subscription record this deployment serves.",
    )
    infra_config = models.ForeignKey(
        InfrastructureConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deployments",
    )

    # ---- State ----
    deployment_type = models.CharField(
        max_length=32,
        choices=DeploymentType.choices,
        default=DeploymentType.PROVISION,
        db_index=True,
    )
    status = models.CharField(
        max_length=32,
        choices=DeploymentStatus.choices,
        default=DeploymentStatus.QUEUED,
        db_index=True,
    )

    # ---- Version Tracking ----
    from_version = models.CharField(
        max_length=50,
        blank=True,
        help_text="Version being replaced (for UPGRADE/ROLLBACK operations).",
    )
    to_version = models.CharField(
        max_length=50,
        blank=True,
        help_text="Target version being deployed.",
    )

    # ---- Runtime Info ----
    container_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Docker container ID or K8s Pod name once provisioned.",
    )
    service_url = models.URLField(
        blank=True,
        null=True,
        help_text="Public URL of the deployed product instance.",
    )
    internal_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Internal network IP of the deployed service.",
    )
    port = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Host port the service is listening on.",
    )

    # ---- Timing ----
    queued_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the deployment was queued.",
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when execution began.",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the deployment succeeded or failed.",
    )

    # ---- Failure Info ----
    error_message = models.TextField(
        blank=True,
        help_text="Human-readable error description on FAILED status.",
    )
    error_code = models.CharField(
        max_length=50,
        blank=True,
        help_text="Machine-readable error code for programmatic retry logic.",
    )
    retry_count = models.PositiveSmallIntegerField(
        default=0,
        help_text="Number of automatic retry attempts made.",
    )
    max_retries = models.PositiveSmallIntegerField(
        default=3,
        help_text="Maximum automatic retries before FAILED is final.",
    )

    # ---- Celery Task ----
    celery_task_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Celery task ID for monitoring/revocation.",
    )

    class Meta(BaseModel.Meta):
        db_table = "deployments_records"
        verbose_name = _("Deployment Record")
        verbose_name_plural = _("Deployment Records")
        ordering = ["-queued_at"]

    def __str__(self) -> str:
        return (
            f"Deployment[{self.deployment_type}] "
            f"{self.tenant_product} → {self.to_version} ({self.status})"
        )

    @property
    def duration_seconds(self) -> float | None:
        """Return deployment duration in seconds if completed."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def can_retry(self) -> bool:
        """Return True if auto-retry is still possible."""
        return self.status == DeploymentStatus.FAILED and self.retry_count < self.max_retries


# ============================================================
# DEPLOYMENT LOG
# ============================================================

class DeploymentLog(models.Model):
    """
    Append-only structured log entries for a DeploymentRecord.

    IMMUTABLE: No update() or save() on existing rows.
    Insert new rows only. Provides a full execution audit trail.
    """

    id = models.BigAutoField(primary_key=True)
    deployment = models.ForeignKey(
        DeploymentRecord,
        on_delete=models.CASCADE,
        related_name="logs",
    )
    level = models.CharField(
        max_length=10,
        choices=LogLevel.choices,
        default=LogLevel.INFO,
        db_index=True,
    )
    step = models.CharField(
        max_length=100,
        blank=True,
        help_text="Deployment step name (e.g., 'IMAGE_PULL', 'ENV_INJECT').",
    )
    message = models.TextField()
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured context data for the log entry.",
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "deployments_logs"
        verbose_name = _("Deployment Log")
        verbose_name_plural = _("Deployment Logs")
        ordering = ["timestamp"]

    def __str__(self) -> str:
        return f"[{self.level}] {self.deployment_id} — {self.step}: {self.message[:80]}"

    def save(self, *args, **kwargs):
        """Prevent updates to existing log entries."""
        if self.pk:
            raise PermissionError(
                "DeploymentLog entries are immutable. "
                "Create a new entry instead of updating."
            )
        super().save(*args, **kwargs)


# ============================================================
# DEPLOYMENT HEALTH CHECK
# ============================================================

class DeploymentHealthCheck(BaseModel):
    """
    Periodic health snapshot of a running deployment.

    Created by the health monitoring Celery beat task.
    Tracks response time, error rate, and system resource usage.
    """

    deployment = models.ForeignKey(
        DeploymentRecord,
        on_delete=models.CASCADE,
        related_name="health_checks",
    )
    status = models.CharField(
        max_length=20,
        choices=HealthStatus.choices,
        default=HealthStatus.UNKNOWN,
        db_index=True,
    )
    response_time_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Health endpoint response time in milliseconds.",
    )
    cpu_usage_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    memory_usage_mb = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    error_message = models.TextField(
        blank=True,
        help_text="Reason for UNHEALTHY status, if applicable.",
    )
    checked_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta(BaseModel.Meta):
        db_table = "deployments_health_checks"
        verbose_name = _("Deployment Health Check")
        verbose_name_plural = _("Deployment Health Checks")
        ordering = ["-checked_at"]

    def __str__(self) -> str:
        return f"Health[{self.status}] for Deployment {self.deployment_id} at {self.checked_at}"
