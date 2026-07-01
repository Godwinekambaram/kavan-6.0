"""
KAVAN v6.0 — Deployments Signals
============================================================
Layer 6: Django signals for deployment lifecycle events.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.deployments.models import DeploymentRecord, DeploymentStatus

logger = logging.getLogger("kavan.deployments.signals")


@receiver(post_save, sender=DeploymentRecord)
def on_deployment_record_save(
    sender, instance: DeploymentRecord, created: bool, **kwargs
):
    """
    Log deployment lifecycle transitions to the central logger
    for audit/observability.
    """
    if created:
        logger.info(
            "Deployment record registered.",
            extra={
                "kavan_data": {
                    "event": "DEPLOYMENT_QUEUED",
                    "deployment_id": str(instance.id),
                    "type": instance.deployment_type,
                    "target_version": instance.to_version,
                }
            },
        )
    else:
        logger.info(
            "Deployment record state transitioned.",
            extra={
                "kavan_data": {
                    "event": f"DEPLOYMENT_{instance.status}",
                    "deployment_id": str(instance.id),
                    "status": instance.status,
                }
            },
        )
