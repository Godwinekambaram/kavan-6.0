from django.db import models
from backend.apps.tenants.services.tenant_context_service import TenantContextService

class TenantScopedManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        current_tenant = TenantContextService.get_current_tenant()
        if current_tenant:
            return qs.filter(tenant=current_tenant)
        return qs

class UnscopedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()
