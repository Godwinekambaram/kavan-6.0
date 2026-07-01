"""
KAVAN v6.0 — Deployment Engine Service
============================================================
Layer 6: Deployment & Provisioning Engine Business Logic

Services:
  - DeploymentEngineService : Core provisioning/upgrade/decommission logic
  - DeploymentHealthService : Health monitoring and auto-repair
  - InfrastructureService   : Infra config management

Rules (Clean Architecture):
  - All business logic lives here — not in tasks, views, or models.
  - Services drive status transitions on DeploymentRecord.
  - Services append structured logs via DeploymentLogRepository.
  - Infrastructure drivers are injected via the driver pattern
    (DockerDriver, KubernetesDriver) to remain swappable.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from django.db import transaction

from apps.deployments.models import (
    DeploymentRecord,
    DeploymentStatus,
    DeploymentType,
    HealthStatus,
    InfrastructureConfig,
    InfrastructureProvider,
)
from apps.deployments.repositories import (
    DeploymentHealthCheckRepository,
    DeploymentLogRepository,
    DeploymentRepository,
    InfrastructureConfigRepository,
)
from common.exceptions.base import KAVANException, ValidationException
from common.services.base_service import BaseService

logger = logging.getLogger("kavan.deployments.services")


# ============================================================
# CUSTOM EXCEPTIONS
# ============================================================

class DeploymentNotFoundException(KAVANException):
    """Raised when a deployment record is not found."""
    error_code = "DEP_001"

    def __init__(self, message="Deployment not found."):
        super().__init__(message)


class DeploymentAlreadyRunningException(KAVANException):
    """Raised when trying to provision over an already-running deployment."""
    error_code = "DEP_002"

    def __init__(self, message="A deployment is already running for this subscription."):
        super().__init__(message)


class DeploymentTransitionException(KAVANException):
    """Raised when an invalid status transition is attempted."""
    error_code = "DEP_003"

    def __init__(self, message="Invalid deployment status transition."):
        super().__init__(message)


class InfrastructureDriverException(KAVANException):
    """Raised when an infrastructure driver operation fails."""
    error_code = "DEP_004"

    def __init__(self, message="Infrastructure operation failed."):
        super().__init__(message)


# ============================================================
# INFRASTRUCTURE SERVICE
# ============================================================

class InfrastructureService(BaseService):
    """
    Manages per-tenant infrastructure configuration.
    """

    @classmethod
    def get_or_provision_infra(cls, tenant) -> InfrastructureConfig:
        """
        Return the existing infrastructure config for a tenant,
        or create a default KAVAN Cloud config if none exists.
        """
        config = InfrastructureConfigRepository.get_or_create_default(tenant)
        logger.info(
            "Infrastructure config resolved.",
            extra={
                "kavan_data": {
                    "tenant_id": str(tenant.id),
                    "provider": config.provider,
                    "region": config.region,
                }
            },
        )
        return config

    @classmethod
    @transaction.atomic
    def update_infra_config(cls, tenant, **kwargs) -> InfrastructureConfig:
        """
        Update the infrastructure configuration for a tenant.
        Validates that resource allocations meet minimum requirements.
        """
        config = InfrastructureConfigRepository.get_by_tenant(tenant)
        if not config:
            raise DeploymentNotFoundException(
                "Infrastructure config not found for this tenant."
            )

        min_memory = kwargs.get("allocated_memory_mb", config.allocated_memory_mb)
        min_cpu = kwargs.get("allocated_cpu_cores", config.allocated_cpu_cores)

        if min_memory < 512:
            raise ValidationException("Minimum memory allocation is 512 MB.")
        if min_cpu < 1:
            raise ValidationException("Minimum CPU allocation is 1 core.")

        return InfrastructureConfigRepository.update(config, **kwargs)


# ============================================================
# DEPLOYMENT ENGINE SERVICE
# ============================================================

class DeploymentEngineService(BaseService):
    """
    Core deployment engine driving the provisioning lifecycle.

    Operates as a state machine on DeploymentRecord objects.
    Each method transitions the record through defined stages
    and logs every action for full auditability.

    Infrastructure operations are performed via provider-specific
    driver classes (Docker, K8s, etc.). In this implementation,
    the driver layer is abstracted through _get_driver().
    """

    # ---- PUBLIC API ----

    @classmethod
    @transaction.atomic
    def create_deployment(
        cls,
        subscription_id: str,
        deployment_type: str = DeploymentType.PROVISION,
        from_version: str = "",
        to_version: str = "",
    ) -> DeploymentRecord:
        """
        Create a new DeploymentRecord in QUEUED status.

        Called by Celery tasks (tasks.py) which are triggered by
        the MarketplaceService when a tenant installs a product.

        Args:
            subscription_id:  UUID of the TenantProduct subscription.
            deployment_type:  DeploymentType choice.
            from_version:     Source version (for upgrades).
            to_version:       Target version being deployed.

        Returns:
            DeploymentRecord in QUEUED status.
        """
        from apps.marketplace.models.product import TenantProduct

        try:
            subscription = TenantProduct.objects.select_related(
                "tenant", "current_version", "product"
            ).get(id=subscription_id)
        except TenantProduct.DoesNotExist:
            raise DeploymentNotFoundException(
                f"Subscription {subscription_id} not found."
            )

        # Prevent duplicate active deployments
        active = DeploymentRepository.get_active_deployment(subscription_id)
        if active and deployment_type == DeploymentType.PROVISION:
            raise DeploymentAlreadyRunningException()

        # Resolve infra config
        infra = InfrastructureConfigRepository.get_or_create_default(
            subscription.tenant
        )

        # Resolve version strings
        to_ver = to_version or (
            subscription.current_version.version_string
            if subscription.current_version
            else ""
        )

        deployment = DeploymentRepository.create(
            tenant_product=subscription,
            infra_config=infra,
            deployment_type=deployment_type,
            status=DeploymentStatus.QUEUED,
            from_version=from_version,
            to_version=to_ver,
        )

        DeploymentLogRepository.append(
            deployment=deployment,
            level="INFO",
            step="QUEUED",
            message=f"Deployment queued. Type={deployment_type}, Target={to_ver}",
            metadata={"infra_provider": infra.provider, "region": infra.region},
        )

        logger.info(
            "Deployment created and queued.",
            extra={
                "kavan_data": {
                    "deployment_id": str(deployment.id),
                    "subscription_id": subscription_id,
                    "type": deployment_type,
                    "version": to_ver,
                }
            },
        )

        return deployment

    @classmethod
    @transaction.atomic
    def execute_deployment(cls, deployment_id: str) -> DeploymentRecord:
        """
        Execute a queued deployment end-to-end.

        Drives the following transitions:
          QUEUED → PROVISIONING → PULLING_IMAGE → CONFIGURING → STARTING → RUNNING

        Called by the Celery task after create_deployment().
        Each stage is logged for full auditability.

        Args:
            deployment_id: UUID of the DeploymentRecord.

        Returns:
            Updated DeploymentRecord in RUNNING (or FAILED) status.
        """
        deployment = DeploymentRepository.get_by_id(deployment_id)
        if not deployment:
            raise DeploymentNotFoundException()

        if deployment.status not in (DeploymentStatus.QUEUED, DeploymentStatus.ROLLBACK):
            raise DeploymentTransitionException(
                f"Cannot execute a deployment in '{deployment.status}' status."
            )

        try:
            # Stage 1: Provisioning
            deployment = cls._stage_provisioning(deployment)

            # Stage 2: Pull image
            deployment = cls._stage_pull_image(deployment)

            # Stage 3: Configure environment
            deployment = cls._stage_configure(deployment)

            # Stage 4: Start services
            deployment = cls._stage_start(deployment)

            # Stage 5: Mark RUNNING and activate subscription
            deployment = cls._stage_complete(deployment)

        except Exception as exc:
            deployment = cls._handle_failure(deployment, exc)
            raise

        return deployment

    @classmethod
    @transaction.atomic
    def execute_upgrade(
        cls,
        deployment_id: str,
        from_version: str,
    ) -> DeploymentRecord:
        """
        Upgrade a RUNNING deployment to the version in current_version.

        Transitions: RUNNING → UPGRADING → RUNNING

        Args:
            deployment_id: UUID of the active DeploymentRecord.
            from_version:  Previous version (for rollback reference).

        Returns:
            Updated DeploymentRecord.
        """
        deployment = DeploymentRepository.get_by_id(deployment_id)
        if not deployment:
            raise DeploymentNotFoundException()

        if deployment.status != DeploymentStatus.RUNNING:
            raise DeploymentTransitionException(
                "Only RUNNING deployments can be upgraded."
            )

        # Transition to UPGRADING
        deployment = DeploymentRepository.transition_status(
            deployment, DeploymentStatus.UPGRADING, from_version=from_version
        )
        DeploymentLogRepository.append(
            deployment=deployment,
            level="INFO",
            step="UPGRADE_STARTED",
            message=f"Upgrade initiated from {from_version} to {deployment.to_version}.",
        )

        try:
            driver = cls._get_driver(deployment)
            result = driver.upgrade(deployment)

            DeploymentRepository.transition_status(
                deployment,
                DeploymentStatus.RUNNING,
                container_id=result.get("container_id", deployment.container_id),
            )
            DeploymentLogRepository.append(
                deployment=deployment,
                level="INFO",
                step="UPGRADE_COMPLETE",
                message="Upgrade completed successfully.",
                metadata=result,
            )
            deployment.refresh_from_db()
            return deployment

        except Exception as exc:
            return cls._handle_failure(deployment, exc)

    @classmethod
    @transaction.atomic
    def execute_rollback(
        cls,
        deployment: DeploymentRecord,
        target_version: str,
    ) -> DeploymentRecord:
        """
        Roll a deployment back to a specified version.

        Transitions: RUNNING/FAILED → ROLLBACK → RUNNING

        Args:
            deployment:      Active DeploymentRecord.
            target_version:  Version string to roll back to.

        Returns:
            Updated DeploymentRecord.
        """
        deployment = DeploymentRepository.transition_status(
            deployment,
            DeploymentStatus.ROLLBACK,
            from_version=deployment.to_version,
            to_version=target_version,
        )

        DeploymentLogRepository.append(
            deployment=deployment,
            level="WARNING",
            step="ROLLBACK_STARTED",
            message=f"Rollback initiated. Target={target_version}.",
        )

        try:
            driver = cls._get_driver(deployment)
            result = driver.rollback(deployment, target_version)

            DeploymentRepository.transition_status(
                deployment,
                DeploymentStatus.RUNNING,
                container_id=result.get("container_id", deployment.container_id),
            )
            DeploymentLogRepository.append(
                deployment=deployment,
                level="INFO",
                step="ROLLBACK_COMPLETE",
                message="Rollback completed.",
                metadata=result,
            )
            deployment.refresh_from_db()
            return deployment

        except Exception as exc:
            return cls._handle_failure(deployment, exc)

    @classmethod
    @transaction.atomic
    def decommission(cls, deployment_id: str) -> DeploymentRecord:
        """
        Stop and decommission a running deployment.

        Transitions: RUNNING/STOPPED → STOPPING → STOPPED → DECOMMISSIONED

        Called by the decommission Celery task when a tenant
        cancels their product subscription.
        """
        deployment = DeploymentRepository.get_by_id(deployment_id)
        if not deployment:
            # Nothing to decommission — idempotent
            return None

        if deployment.status == DeploymentStatus.DECOMMISSIONED:
            return deployment

        deployment = DeploymentRepository.transition_status(
            deployment, DeploymentStatus.STOPPING
        )

        DeploymentLogRepository.append(
            deployment=deployment,
            level="INFO",
            step="DECOMMISSION_STARTED",
            message="Decommission initiated.",
        )

        try:
            driver = cls._get_driver(deployment)
            driver.stop(deployment)

            deployment = DeploymentRepository.transition_status(
                deployment, DeploymentStatus.STOPPED
            )
            deployment = DeploymentRepository.transition_status(
                deployment, DeploymentStatus.DECOMMISSIONED
            )

            DeploymentLogRepository.append(
                deployment=deployment,
                level="INFO",
                step="DECOMMISSION_COMPLETE",
                message="Service stopped and decommissioned.",
            )

        except Exception as exc:
            return cls._handle_failure(deployment, exc)

        return deployment

    # ---- PRIVATE STAGE METHODS ----

    @classmethod
    def _stage_provisioning(cls, deployment: DeploymentRecord) -> DeploymentRecord:
        """Transition to PROVISIONING and allocate infrastructure."""
        deployment = DeploymentRepository.transition_status(
            deployment, DeploymentStatus.PROVISIONING
        )
        DeploymentLogRepository.append(
            deployment=deployment,
            level="INFO",
            step="PROVISIONING",
            message="Infrastructure provisioning started.",
            metadata={
                "provider": deployment.infra_config.provider if deployment.infra_config else "UNKNOWN",
                "region": deployment.infra_config.region if deployment.infra_config else "UNKNOWN",
            },
        )

        driver = cls._get_driver(deployment)
        driver.provision_infrastructure(deployment)

        return deployment

    @classmethod
    def _stage_pull_image(cls, deployment: DeploymentRecord) -> DeploymentRecord:
        """Transition to PULLING_IMAGE and pull the container image."""
        deployment = DeploymentRepository.transition_status(
            deployment, DeploymentStatus.PULLING_IMAGE
        )

        version = deployment.tenant_product.current_version
        image_ref = version.docker_image if version else "unknown"

        DeploymentLogRepository.append(
            deployment=deployment,
            level="INFO",
            step="IMAGE_PULL",
            message=f"Pulling container image: {image_ref}",
            metadata={"image": image_ref},
        )

        driver = cls._get_driver(deployment)
        driver.pull_image(deployment, image_ref)

        return deployment

    @classmethod
    def _stage_configure(cls, deployment: DeploymentRecord) -> DeploymentRecord:
        """Transition to CONFIGURING and inject environment variables."""
        deployment = DeploymentRepository.transition_status(
            deployment, DeploymentStatus.CONFIGURING
        )
        DeploymentLogRepository.append(
            deployment=deployment,
            level="INFO",
            step="ENV_INJECT",
            message="Injecting environment configuration.",
        )

        driver = cls._get_driver(deployment)
        driver.configure(deployment)

        return deployment

    @classmethod
    def _stage_start(cls, deployment: DeploymentRecord) -> DeploymentRecord:
        """Transition to STARTING and launch the service containers."""
        deployment = DeploymentRepository.transition_status(
            deployment, DeploymentStatus.STARTING
        )
        DeploymentLogRepository.append(
            deployment=deployment,
            level="INFO",
            step="SERVICE_START",
            message="Starting service containers.",
        )

        driver = cls._get_driver(deployment)
        result = driver.start(deployment)

        # Store runtime info
        DeploymentRepository.update(
            deployment,
            container_id=result.get("container_id", ""),
            service_url=result.get("service_url", ""),
            internal_ip=result.get("internal_ip", ""),
            port=result.get("port"),
        )

        return deployment

    @classmethod
    def _stage_complete(cls, deployment: DeploymentRecord) -> DeploymentRecord:
        """Transition to RUNNING and activate the subscription."""
        deployment = DeploymentRepository.transition_status(
            deployment, DeploymentStatus.RUNNING
        )
        DeploymentLogRepository.append(
            deployment=deployment,
            level="INFO",
            step="RUNNING",
            message="Deployment complete. Service is now running.",
            metadata={"service_url": deployment.service_url},
        )

        # Activate the TenantProduct subscription
        subscription = deployment.tenant_product
        subscription.activate()

        logger.info(
            "Deployment completed successfully.",
            extra={
                "kavan_data": {
                    "deployment_id": str(deployment.id),
                    "service_url": deployment.service_url,
                }
            },
        )

        deployment.refresh_from_db()
        return deployment

    @classmethod
    def _handle_failure(
        cls,
        deployment: DeploymentRecord,
        exc: Exception,
    ) -> DeploymentRecord:
        """Mark deployment as FAILED, log the error, schedule retry if budget remains."""
        error_msg = str(exc)

        deployment = DeploymentRepository.transition_status(
            deployment,
            DeploymentStatus.FAILED,
            error_message=error_msg,
            retry_count=deployment.retry_count + 1,
        )

        DeploymentLogRepository.append(
            deployment=deployment,
            level="ERROR",
            step="FAILURE",
            message=f"Deployment failed: {error_msg}",
            metadata={"exception_type": type(exc).__name__},
        )

        logger.error(
            "Deployment failed.",
            extra={
                "kavan_data": {
                    "deployment_id": str(deployment.id),
                    "error": error_msg,
                    "retry_count": deployment.retry_count,
                    "can_retry": deployment.can_retry,
                }
            },
        )

        # Schedule retry if budget remains
        if deployment.can_retry:
            cls._schedule_retry(deployment)

        return deployment

    @classmethod
    def _schedule_retry(cls, deployment: DeploymentRecord) -> None:
        """Schedule a retry via Celery with exponential backoff."""
        try:
            from apps.deployments.tasks import execute_deployment_task
            countdown = 60 * (2 ** deployment.retry_count)  # Exponential backoff
            execute_deployment_task.apply_async(
                args=[str(deployment.id)],
                countdown=countdown,
            )
            logger.info(
                "Deployment retry scheduled.",
                extra={
                    "kavan_data": {
                        "deployment_id": str(deployment.id),
                        "retry_count": deployment.retry_count,
                        "backoff_seconds": countdown,
                    }
                },
            )
        except ImportError:
            logger.warning("Celery not available. Retry not scheduled.")

    @staticmethod
    def _get_driver(deployment: DeploymentRecord):
        """
        Return the appropriate infrastructure driver for the deployment.

        The driver is selected based on the InfrastructureConfig.provider.
        Falls back to DockerDriver for development/local environments.
        """
        from apps.deployments.drivers import (
            DockerDriver,
            KavanCloudDriver,
        )

        provider = (
            deployment.infra_config.provider
            if deployment.infra_config
            else InfrastructureProvider.DOCKER_LOCAL
        )

        driver_map = {
            InfrastructureProvider.KAVAN_CLOUD: KavanCloudDriver,
            InfrastructureProvider.DOCKER_LOCAL: DockerDriver,
        }

        driver_class = driver_map.get(provider, DockerDriver)
        return driver_class(deployment)


# ============================================================
# DEPLOYMENT HEALTH SERVICE
# ============================================================

class DeploymentHealthService(BaseService):
    """
    Monitors the health of running deployments and triggers
    auto-repair actions when services become unhealthy.

    Called by the Celery beat scheduler every N minutes.
    """

    @classmethod
    def run_health_check(cls, deployment_id: str) -> DeploymentHealthCheck:
        """
        Execute a health check against a running deployment.

        Fetches the service health endpoint, records CPU/memory
        metrics, and updates the HealthStatus.

        If UNHEALTHY, triggers an auto-repair sequence.

        Args:
            deployment_id: UUID of the DeploymentRecord.

        Returns:
            DeploymentHealthCheck snapshot.
        """
        from apps.deployments.models import DeploymentHealthCheck

        deployment = DeploymentRepository.get_by_id(deployment_id)
        if not deployment or deployment.status != DeploymentStatus.RUNNING:
            return None

        try:
            driver = DeploymentEngineService._get_driver(deployment)
            metrics = driver.get_health_metrics(deployment)

            health_status = cls._evaluate_health(metrics)

            check = DeploymentHealthCheckRepository.record_check(
                deployment=deployment,
                status=health_status,
                response_time_ms=metrics.get("response_time_ms"),
                cpu_usage_percent=metrics.get("cpu_usage_percent"),
                memory_usage_mb=metrics.get("memory_usage_mb"),
            )

            if health_status == HealthStatus.UNHEALTHY:
                cls._trigger_auto_repair(deployment)
            elif health_status == HealthStatus.DEGRADED:
                logger.warning(
                    "Deployment is degraded.",
                    extra={"kavan_data": {"deployment_id": str(deployment.id), "metrics": metrics}},
                )

            return check

        except Exception as exc:
            logger.error(
                "Health check failed for deployment %s: %s",
                deployment_id,
                str(exc),
            )
            return DeploymentHealthCheckRepository.record_check(
                deployment=deployment,
                status=HealthStatus.UNKNOWN,
                error_message=str(exc),
            )

    @staticmethod
    def _evaluate_health(metrics: dict) -> str:
        """
        Determine health status from raw metrics.

        Rules:
          - HEALTHY   : response_time_ms < 2000 AND cpu < 85%
          - DEGRADED  : response_time_ms 2000-5000 OR cpu 85-95%
          - UNHEALTHY : response_time_ms > 5000 OR cpu > 95% OR no response
        """
        if metrics.get("unreachable"):
            return HealthStatus.UNHEALTHY

        rt = metrics.get("response_time_ms", 0)
        cpu = metrics.get("cpu_usage_percent", 0)

        if rt > 5000 or cpu > 95:
            return HealthStatus.UNHEALTHY
        if rt > 2000 or cpu > 85:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    @staticmethod
    def _trigger_auto_repair(deployment: DeploymentRecord) -> None:
        """Queue an auto-repair (HEALTH_REPAIR) deployment via Celery."""
        try:
            from apps.deployments.tasks import health_repair_task
            health_repair_task.delay(str(deployment.id))
        except ImportError:
            logger.warning("Celery unavailable. Auto-repair not triggered.")
