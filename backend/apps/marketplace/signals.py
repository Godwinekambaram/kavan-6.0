"""
KAVAN v6.0 — Marketplace Signals
============================================================
Layer 5: Django signals for marketplace lifecycle events.

Signals provide decoupled event hooks — marketplace models
emit events that are consumed by audit, notifications,
and Layer 6 deployment triggers.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.marketplace.models.product import (
    Product,
    ProductStatus,
    TenantProduct,
    TenantProductStatus,
)

logger = logging.getLogger("kavan.marketplace.signals")


@receiver(post_save, sender=Product)
def on_product_status_change(sender, instance: Product, created: bool, **kwargs):
    """
    Emit an audit event whenever a product status changes.
    """
    if created:
        logger.info(
            "New product created in marketplace catalogue.",
            extra={
                "kavan_data": {
                    "event": "PRODUCT_CREATED",
                    "product_id": str(instance.id),
                    "code": instance.code,
                }
            },
        )
    else:
        logger.info(
            "Product updated.",
            extra={
                "kavan_data": {
                    "event": "PRODUCT_UPDATED",
                    "product_id": str(instance.id),
                    "status": instance.status,
                }
            },
        )


@receiver(post_save, sender=TenantProduct)
def on_tenant_product_status_change(
    sender, instance: TenantProduct, created: bool, **kwargs
):
    """
    Log subscription lifecycle events for audit and billing hooks.
    """
    if created:
        logger.info(
            "New product subscription created.",
            extra={
                "kavan_data": {
                    "event": "SUBSCRIPTION_CREATED",
                    "subscription_id": str(instance.id),
                    "tenant_id": str(instance.tenant_id),
                    "product_id": str(instance.product_id),
                }
            },
        )
    elif instance.status == TenantProductStatus.ACTIVE:
        logger.info(
            "Product subscription activated.",
            extra={
                "kavan_data": {
                    "event": "SUBSCRIPTION_ACTIVATED",
                    "subscription_id": str(instance.id),
                }
            },
        )
    elif instance.status == TenantProductStatus.CANCELLED:
        logger.info(
            "Product subscription cancelled.",
            extra={
                "kavan_data": {
                    "event": "SUBSCRIPTION_CANCELLED",
                    "subscription_id": str(instance.id),
                }
            },
        )
