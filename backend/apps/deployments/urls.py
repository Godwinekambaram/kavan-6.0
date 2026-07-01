"""
KAVAN v6.0 — Deployments URL Configuration
============================================================
Layer 6: Deployment & Provisioning Engine API Routes

Tenant Routes          → /api/v1/deployments/...
Platform Admin Routes  → /api/v1/deployments/admin/...
"""

from django.urls import path

from apps.deployments.views import (
    AdminDeploymentHealthSummaryView,
    AdminDeploymentListView,
    TenantDeploymentDetailView,
    TenantDeploymentHealthView,
    TenantDeploymentListView,
    TenantDeploymentLogsView,
    TenantDeploymentRetryView,
    TenantDeploymentRollbackView,
    TenantInfraConfigView,
)

app_name = "deployments"

urlpatterns = [
    # --------------------------------------------------------
    # TENANT — Infrastructure & Deployment Access
    # --------------------------------------------------------

    # GET/PATCH /api/v1/deployments/infra/
    path(
        "infra/",
        TenantInfraConfigView.as_view(),
        name="infra-config",
    ),

    # GET       /api/v1/deployments/
    path(
        "",
        TenantDeploymentListView.as_view(),
        name="deployment-list",
    ),

    # GET       /api/v1/deployments/<uuid:deployment_id>/
    path(
        "<uuid:deployment_id>/",
        TenantDeploymentDetailView.as_view(),
        name="deployment-detail",
    ),

    # GET       /api/v1/deployments/<uuid:deployment_id>/logs/
    path(
        "<uuid:deployment_id>/logs/",
        TenantDeploymentLogsView.as_view(),
        name="deployment-logs",
    ),

    # GET       /api/v1/deployments/<uuid:deployment_id>/health/
    path(
        "<uuid:deployment_id>/health/",
        TenantDeploymentHealthView.as_view(),
        name="deployment-health",
    ),

    # POST      /api/v1/deployments/<uuid:deployment_id>/rollback/
    path(
        "<uuid:deployment_id>/rollback/",
        TenantDeploymentRollbackView.as_view(),
        name="deployment-rollback",
    ),

    # POST      /api/v1/deployments/<uuid:deployment_id>/retry/
    path(
        "<uuid:deployment_id>/retry/",
        TenantDeploymentRetryView.as_view(),
        name="deployment-retry",
    ),

    # --------------------------------------------------------
    # PLATFORM ADMIN — Deployment Supervision
    # --------------------------------------------------------

    # GET       /api/v1/deployments/admin/all/
    path(
        "admin/all/",
        AdminDeploymentListView.as_view(),
        name="admin-deployment-list",
    ),

    # GET       /api/v1/deployments/admin/health-summary/
    path(
        "admin/health-summary/",
        AdminDeploymentHealthSummaryView.as_view(),
        name="admin-health-summary",
    ),
]
