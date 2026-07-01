"""
KAVAN v6.0 — Deployment Celery Tasks
============================================================
Layer 6: Async task definitions for the Deployment Engine.

All deployment operations are executed asynchronously via Celery.
Tasks are triggered by:
  - MarketplaceService (install/upgrade/uninstall)
  - Celery Beat (health checks)
  - DeploymentEngineService (retry on failure)

Task Routing:
  All deployment tasks are routed to the 'deployments' Celery queue
  to allow separate worker scaling from the main application queue.
"""

import logging

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

logger = logging.getLogger("kavan.deployments.tasks")


# ============================================================
# PROVISIONING TASK
# ============================================================

@shared_task(
    bind=True,
    name="deployments.provision_product",
    queue="deployments",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def provision_product_task(self, subscription_id: str) -> dict:
    """
    Celery task: Provision a new product deployment for a tenant.

    Called by MarketplaceService.install_product() after the
    TenantProduct subscription record is created.

    Steps:
      1. Create a QUEUED DeploymentRecord.
      2. Execute the full provisioning pipeline.

    Args:
        subscription_id: UUID str of the TenantProduct record.

    Returns:
        Dict with deployment_id and final status.
    """
    from apps.deployments.services import (
        DeploymentEngineService,
        DeploymentAlreadyRunningException,
    )
    from apps.deployments.models import DeploymentType

    logger.info(
        "Provisioning task started.",
        extra={"kavan_data": {"subscription_id": subscription_id}},
    )

    try:
        # Create the deployment record
        deployment = DeploymentEngineService.create_deployment(
            subscription_id=subscription_id,
            deployment_type=DeploymentType.PROVISION,
        )

        # Execute the provisioning pipeline
        deployment = DeploymentEngineService.execute_deployment(str(deployment.id))

        logger.info(
            "Provisioning task completed.",
            extra={
                "kavan_data": {
                    "deployment_id": str(deployment.id),
                    "status": deployment.status,
                }
            },
        )

        return {
            "deployment_id": str(deployment.id),
            "status": deployment.status,
            "service_url": deployment.service_url,
        }

    except DeploymentAlreadyRunningException:
        logger.warning(
            "Provisioning skipped — deployment already running.",
            extra={"kavan_data": {"subscription_id": subscription_id}},
        )
        return {"status": "SKIPPED", "reason": "already_running"}

    except Exception as exc:
        logger.error(
            "Provisioning task failed: %s",
            str(exc),
            extra={"kavan_data": {"subscription_id": subscription_id}},
        )
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.critical(
                "Provisioning task exhausted all retries for subscription %s.",
                subscription_id,
            )
            return {"status": "FAILED", "error": str(exc)}


# ============================================================
# UPGRADE TASK
# ============================================================

@shared_task(
    bind=True,
    name="deployments.upgrade_product",
    queue="deployments",
    max_retries=2,
    default_retry_delay=120,
    acks_late=True,
)
def upgrade_product_task(self, subscription_id: str, from_version: str) -> dict:
    """
    Celery task: Upgrade a tenant's product to the version currently
    set on the TenantProduct subscription.

    Args:
        subscription_id: UUID str of the TenantProduct record.
        from_version:    The version being replaced.

    Returns:
        Dict with deployment_id and final status.
    """
    from apps.deployments.services import DeploymentEngineService
    from apps.deployments.models import DeploymentType
    from apps.deployments.repositories import DeploymentRepository

    logger.info(
        "Upgrade task started.",
        extra={
            "kavan_data": {
                "subscription_id": subscription_id,
                "from_version": from_version,
            }
        },
    )

    try:
        # Create an UPGRADE deployment record
        deployment = DeploymentEngineService.create_deployment(
            subscription_id=subscription_id,
            deployment_type=DeploymentType.UPGRADE,
            from_version=from_version,
        )

        # Find the active running deployment to upgrade
        active = DeploymentRepository.get_active_deployment(subscription_id)

        if active:
            deployment = DeploymentEngineService.execute_upgrade(
                str(active.id),
                from_version=from_version,
            )
        else:
            # No active deployment — fall back to full provision
            deployment = DeploymentEngineService.execute_deployment(str(deployment.id))

        logger.info(
            "Upgrade task completed.",
            extra={
                "kavan_data": {
                    "deployment_id": str(deployment.id),
                    "status": deployment.status,
                }
            },
        )

        return {
            "deployment_id": str(deployment.id),
            "status": deployment.status,
        }

    except Exception as exc:
        logger.error("Upgrade task failed: %s", str(exc))
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            return {"status": "FAILED", "error": str(exc)}


# ============================================================
# DECOMMISSION TASK
# ============================================================

@shared_task(
    bind=True,
    name="deployments.decommission_product",
    queue="deployments",
    max_retries=2,
    default_retry_delay=60,
    acks_late=True,
)
def decommission_product_task(self, subscription_id: str) -> dict:
    """
    Celery task: Decommission a product deployment when a tenant
    cancels their subscription.

    Args:
        subscription_id: UUID str of the TenantProduct record.

    Returns:
        Dict with deployment_id and final status.
    """
    from apps.deployments.services import DeploymentEngineService
    from apps.deployments.repositories import DeploymentRepository

    logger.info(
        "Decommission task started.",
        extra={"kavan_data": {"subscription_id": subscription_id}},
    )

    try:
        active = DeploymentRepository.get_active_deployment(subscription_id)

        if not active:
            logger.info(
                "No active deployment found. Decommission is a no-op.",
                extra={"kavan_data": {"subscription_id": subscription_id}},
            )
            return {"status": "NO_OP"}

        deployment = DeploymentEngineService.decommission(str(active.id))

        return {
            "deployment_id": str(deployment.id) if deployment else None,
            "status": "DECOMMISSIONED",
        }

    except Exception as exc:
        logger.error("Decommission task failed: %s", str(exc))
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            return {"status": "FAILED", "error": str(exc)}


# ============================================================
# EXECUTE DEPLOYMENT TASK (Retry / Direct Execution)
# ============================================================

@shared_task(
    bind=True,
    name="deployments.execute_deployment",
    queue="deployments",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def execute_deployment_task(self, deployment_id: str) -> dict:
    """
    Celery task: Execute a specific DeploymentRecord (by ID).
    Used for retry flows and direct execution hooks.

    Args:
        deployment_id: UUID str of the DeploymentRecord.
    """
    from apps.deployments.services import DeploymentEngineService

    logger.info(
        "Execute deployment task started.",
        extra={"kavan_data": {"deployment_id": deployment_id}},
    )

    try:
        deployment = DeploymentEngineService.execute_deployment(deployment_id)
        return {"deployment_id": deployment_id, "status": deployment.status}

    except Exception as exc:
        logger.error("Execute deployment task failed: %s", str(exc))
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            return {"status": "FAILED", "error": str(exc)}


# ============================================================
# HEALTH CHECK TASK (Celery Beat)
# ============================================================

@shared_task(
    name="deployments.health_check_all",
    queue="deployments",
)
def health_check_all_deployments_task() -> dict:
    """
    Celery Beat task: Run health checks on ALL running deployments.

    Scheduled every 5 minutes via Celery Beat configuration.
    For large deployments, individual health checks are fanned
    out as separate tasks per deployment.

    Returns:
        Summary dict with counts.
    """
    from apps.deployments.models import DeploymentStatus
    from apps.deployments.repositories import DeploymentRepository

    deployments = DeploymentRepository.get_queryset().filter(
        status=DeploymentStatus.RUNNING
    )

    count = 0
    for dep in deployments:
        health_check_single_task.delay(str(dep.id))
        count += 1

    logger.info(
        "Health check fan-out completed.",
        extra={"kavan_data": {"deployment_count": count}},
    )

    return {"checked": count}


@shared_task(
    name="deployments.health_check_single",
    queue="deployments",
)
def health_check_single_task(deployment_id: str) -> dict:
    """
    Celery task: Run a health check on a single deployment.

    Args:
        deployment_id: UUID str of the DeploymentRecord.
    """
    from apps.deployments.services import DeploymentHealthService

    result = DeploymentHealthService.run_health_check(deployment_id)
    if result:
        return {
            "deployment_id": deployment_id,
            "status": result.status,
            "response_time_ms": result.response_time_ms,
        }
    return {"deployment_id": deployment_id, "status": "SKIPPED"}


@shared_task(
    name="deployments.health_repair",
    queue="deployments",
)
def health_repair_task(deployment_id: str) -> dict:
    """
    Celery task: Attempt to auto-repair an unhealthy deployment.

    Creates a HEALTH_REPAIR DeploymentRecord and runs a restart
    sequence to recover the failing service.

    Args:
        deployment_id: UUID str of the unhealthy DeploymentRecord.
    """
    from apps.deployments.services import DeploymentEngineService
    from apps.deployments.models import DeploymentType
    from apps.deployments.repositories import DeploymentRepository

    logger.warning(
        "Health repair task triggered.",
        extra={"kavan_data": {"deployment_id": deployment_id}},
    )

    deployment = DeploymentRepository.get_by_id(deployment_id)
    if not deployment:
        return {"status": "NOT_FOUND"}

    try:
        repair_deployment = DeploymentEngineService.create_deployment(
            subscription_id=str(deployment.tenant_product_id),
            deployment_type=DeploymentType.HEALTH_REPAIR,
            from_version=deployment.to_version,
            to_version=deployment.to_version,
        )
        result = DeploymentEngineService.execute_deployment(str(repair_deployment.id))
        return {"status": result.status, "repair_deployment_id": str(repair_deployment.id)}

    except Exception as exc:
        logger.error("Health repair failed: %s", str(exc))
        return {"status": "FAILED", "error": str(exc)}
