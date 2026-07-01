"""
KAVAN v6.0 — API Router (v1)
============================================================
Centralised DRF router for API version 1.
Future layers register their ViewSets here.

Usage:
    # In apps/authentication/urls.py:
    from config.api_router import router
    router.register(r"auth", AuthViewSet, basename="auth")
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

# Create the v1 router
router = DefaultRouter()

# Export the URL patterns for inclusion in urls.py
app_name = "api_v1"

urlpatterns = router.urls + [
    # Layer 2 — Authentication & Identity
    path("auth/", include("backend.apps.authentication.urls", namespace="authentication")),

    # Layer 3 — Tenants
    path("", include("backend.apps.tenants.urls")),

    # Layer 5 — Marketplace & Product Management
    path("marketplace/", include("backend.apps.marketplace.urls", namespace="marketplace")),

    # Layer 6 — Deployment & Provisioning Engine
    path("deployments/", include("backend.apps.deployments.urls", namespace="deployments")),
]
