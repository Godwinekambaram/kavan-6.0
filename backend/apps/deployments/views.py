"""
KAVAN v6.0 — Deployment Engine API Views
============================================================
Layer 6: DRF view controllers for the Deployment Engine.

Endpoints expose read access to deployment records, logs,
and health checks, plus administrative actions (rollback,
manual retry).

All state-changing operations are delegated to services.
Views never interact with models directly.
"""

import logging

from django.utils.decorators import method_decorator

from apps.deployments.repositories import (
    DeploymentHealthCheckRepository,
    DeploymentLogRepository,
    DeploymentRepository,
    InfrastructureConfigRepository,
)
from apps.deployments.serializers import (
    DeploymentHealthCheckSerializer,
    DeploymentLogSerializer,
    DeploymentRecordDetailSerializer,
    DeploymentRecordListSerializer,
    InfrastructureConfigSerializer,
    InfrastructureConfigUpdateSerializer,
    RollbackSerializer,
)
from apps.deployments.services import (
    DeploymentEngineService,
    DeploymentNotFoundException,
    DeploymentTransitionException,
    InfrastructureService,
)
from apps.rbac.decorators import platform_permission, tenant_permission
from common.exceptions.base import ValidationException
from common.views.base import BaseAPIView

logger = logging.getLogger("kavan.deployments.views")


# ============================================================
# INFRASTRUCTURE CONFIG VIEWS
# ============================================================

class TenantInfraConfigView(BaseAPIView):
    """
    GET   /api/v1/deployments/infra/
          Retrieve the current tenant's infrastructure configuration.

    PATCH /api/v1/deployments/infra/
          Update infrastructure resource allocations.
    """

    @method_decorator(tenant_permission("deployments:view"))
    def get(self, request):
        tenant = getattr(request, "tenant", None)
        config = InfrastructureConfigRepository.get_or_create_default(tenant)
        return self.success(
            data=InfrastructureConfigSerializer(config).data,
            message="Infrastructure configuration retrieved.",
        )

    @method_decorator(tenant_permission("deployments:manage"))
    def patch(self, request):
        tenant = getattr(request, "tenant", None)
        serializer = InfrastructureConfigUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return self.error(
                message="Invalid configuration data.",
                errors=serializer.errors,
            )

        try:
            config = InfrastructureService.update_infra_config(
                tenant, **serializer.validated_data
            )
        except (DeploymentNotFoundException, ValidationException) as exc:
            msg = getattr(exc, "message", str(exc))
            return self.error(message=msg)

        return self.success(
            data=InfrastructureConfigSerializer(config).data,
            message="Infrastructure configuration updated.",
        )


# ============================================================
# DEPLOYMENT RECORD VIEWS
# ============================================================

class TenantDeploymentListView(BaseAPIView):
    """
    GET /api/v1/deployments/
    List all deployment records for the current tenant's subscriptions.

    Optional query params:
      ?status=RUNNING
      ?subscription_id=<uuid>
    """

    @method_decorator(tenant_permission("deployments:view"))
    def get(self, request):
        tenant = getattr(request, "tenant", None)

        # Filter by subscriptions belonging to this tenant
        from apps.marketplace.repositories import TenantProductRepository
        subscriptions = TenantProductRepository.get_by_tenant(tenant)
        subscription_ids = subscriptions.values_list("id", flat=True)

        deployments = DeploymentRepository.get_queryset().filter(
            tenant_product_id__in=subscription_ids
        ).select_related("tenant_product", "tenant_product__product").order_by("-queued_at")

        status_filter = request.query_params.get("status")
        if status_filter:
            deployments = deployments.filter(status=status_filter)

        sub_filter = request.query_params.get("subscription_id")
        if sub_filter:
            deployments = deployments.filter(tenant_product_id=sub_filter)

        serializer = DeploymentRecordListSerializer(deployments, many=True)
        return self.success(
            data={"deployments": serializer.data, "count": deployments.count()},
            message="Deployment records retrieved.",
        )


class TenantDeploymentDetailView(BaseAPIView):
    """
    GET /api/v1/deployments/<deployment_id>/
    Retrieve full details, logs, and health for a deployment.
    """

    @method_decorator(tenant_permission("deployments:view"))
    def get(self, request, deployment_id):
        deployment = DeploymentRepository.get_by_id(
            deployment_id,
            select_related=["infra_config", "tenant_product", "tenant_product__product"],
            prefetch_related=["logs", "health_checks"],
        )
        if not deployment:
            return self.not_found("Deployment not found.")

        return self.success(
            data=DeploymentRecordDetailSerializer(deployment).data,
            message="Deployment details retrieved.",
        )


class TenantDeploymentLogsView(BaseAPIView):
    """
    GET /api/v1/deployments/<deployment_id>/logs/
    Stream the execution logs for a deployment.

    Optional query params:
      ?level=ERROR   (filter by log level)
    """

    @method_decorator(tenant_permission("deployments:view"))
    def get(self, request, deployment_id):
        deployment = DeploymentRepository.get_by_id(deployment_id)
        if not deployment:
            return self.not_found("Deployment not found.")

        level = request.query_params.get("level")
        logs = DeploymentLogRepository.get_for_deployment(deployment, level=level)
        serializer = DeploymentLogSerializer(logs, many=True)

        return self.success(
            data={"logs": serializer.data, "count": logs.count()},
            message="Deployment logs retrieved.",
        )


class TenantDeploymentHealthView(BaseAPIView):
    """
    GET /api/v1/deployments/<deployment_id>/health/
    Retrieve the health check history for a deployment.
    """

    @method_decorator(tenant_permission("deployments:view"))
    def get(self, request, deployment_id):
        deployment = DeploymentRepository.get_by_id(deployment_id)
        if not deployment:
            return self.not_found("Deployment not found.")

        checks = DeploymentHealthCheckRepository.get_history(deployment, limit=50)
        serializer = DeploymentHealthCheckSerializer(checks, many=True)
        latest = DeploymentHealthCheckRepository.get_latest(deployment)

        return self.success(
            data={
                "current_status": latest.status if latest else "UNKNOWN",
                "history": serializer.data,
                "count": checks.count(),
            },
            message="Health check history retrieved.",
        )


# ============================================================
# DEPLOYMENT ACTION VIEWS
# ============================================================

class TenantDeploymentRollbackView(BaseAPIView):
    """
    POST /api/v1/deployments/<deployment_id>/rollback/
    Manually trigger a rollback to a specified version.

    Body: { "target_version_string": "v1.1.0" }

    Permissions: deployments:manage
    """

    @method_decorator(tenant_permission("deployments:manage"))
    def post(self, request, deployment_id):
        serializer = RollbackSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error(
                message="Invalid rollback request.",
                errors=serializer.errors,
            )

        deployment = DeploymentRepository.get_by_id(deployment_id)
        if not deployment:
            return self.not_found("Deployment not found.")

        try:
            result = DeploymentEngineService.execute_rollback(
                deployment=deployment,
                target_version=serializer.validated_data["target_version_string"],
            )
        except DeploymentTransitionException as exc:
            return self.error(message=str(exc.message))
        except Exception as exc:
            return self.error(message=f"Rollback failed: {str(exc)}", status=500)

        return self.success(
            data=DeploymentRecordDetailSerializer(result).data,
            message="Rollback initiated.",
        )


class TenantDeploymentRetryView(BaseAPIView):
    """
    POST /api/v1/deployments/<deployment_id>/retry/
    Manually retry a FAILED deployment.

    Permissions: deployments:manage
    """

    @method_decorator(tenant_permission("deployments:manage"))
    def post(self, request, deployment_id):
        deployment = DeploymentRepository.get_by_id(deployment_id)
        if not deployment:
            return self.not_found("Deployment not found.")

        if not deployment.can_retry:
            return self.error(
                message="This deployment cannot be retried. "
                        "Max retries reached or deployment is not in FAILED state.",
                status=409,
            )

        # Queue the retry task
        from apps.deployments.tasks import execute_deployment_task
        execute_deployment_task.delay(str(deployment.id))

        return self.success(
            message="Deployment retry has been queued.",
            data={"deployment_id": deployment_id, "retry_count": deployment.retry_count},
        )


# ============================================================
# PLATFORM ADMIN VIEWS
# ============================================================

class AdminDeploymentListView(BaseAPIView):
    """
    GET /api/v1/deployments/admin/all/
    Platform admin view of all deployments across all tenants.

    Optional query params:
      ?status=FAILED
      ?tenant_id=<uuid>
    """

    @method_decorator(platform_permission("platform:manage_deployments"))
    def get(self, request):
        deployments = DeploymentRepository.get_queryset().select_related(
            "tenant_product", "tenant_product__tenant", "tenant_product__product"
        ).order_by("-queued_at")

        status_filter = request.query_params.get("status")
        if status_filter:
            deployments = deployments.filter(status=status_filter)

        tenant_filter = request.query_params.get("tenant_id")
        if tenant_filter:
            deployments = deployments.filter(
                tenant_product__tenant_id=tenant_filter
            )

        # Paginate
        page = int(request.query_params.get("page", 1))
        limit = min(int(request.query_params.get("limit", 50)), 200)
        offset = (page - 1) * limit
        total = deployments.count()
        paginated = deployments[offset : offset + limit]

        serializer = DeploymentRecordListSerializer(paginated, many=True)
        return self.success(
            data={
                "deployments": serializer.data,
                "total": total,
                "page": page,
                "limit": limit,
            },
            message="All deployment records retrieved.",
        )


class AdminDeploymentHealthSummaryView(BaseAPIView):
    """
    GET /api/v1/deployments/admin/health-summary/
    Platform overview of deployment health across all tenants.
    """

    @method_decorator(platform_permission("platform:manage_deployments"))
    def get(self, request):
        from apps.deployments.models import DeploymentStatus, HealthStatus

        total_running = DeploymentRepository.get_queryset().filter(
            status=DeploymentStatus.RUNNING
        ).count()

        total_failed = DeploymentRepository.get_queryset().filter(
            status=DeploymentStatus.FAILED
        ).count()

        latest_checks = DeploymentHealthCheck = __import__(
            "apps.deployments.models",
            fromlist=["DeploymentHealthCheck"]
        ).DeploymentHealthCheck

        healthy_count = latest_checks.objects.filter(
            status=HealthStatus.HEALTHY
        ).values("deployment_id").distinct().count()

        unhealthy_count = latest_checks.objects.filter(
            status=HealthStatus.UNHEALTHY
        ).values("deployment_id").distinct().count()

        return self.success(
            data={
                "running_deployments": total_running,
                "failed_deployments": total_failed,
                "healthy_services": healthy_count,
                "unhealthy_services": unhealthy_count,
            },
            message="Deployment health summary retrieved.",
        )
