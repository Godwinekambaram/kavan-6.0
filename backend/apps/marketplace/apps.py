"""
KAVAN v6.0 — Marketplace AppConfig
============================================================
Django application configuration for Layer 5.
"""

from django.apps import AppConfig


class MarketplaceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.marketplace"
    verbose_name = "Marketplace"
    label = "marketplace"

    def ready(self):
        """
        Import signals when the app is fully loaded.
        """
        import apps.marketplace.signals  # noqa: F401
