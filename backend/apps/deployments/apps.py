"""
KAVAN v6.0 — Deployments AppConfig
============================================================
Django application configuration for Layer 6.
"""

from django.apps import AppConfig


class DeploymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.deployments"
    verbose_name = "Deployment Engine"
    label = "deployments"

    def ready(self):
        """Import signals on app load."""
        import apps.deployments.signals  # noqa: F401
