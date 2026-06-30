import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.common.models.base_model import BaseModel, SoftDeleteModel

class TenantStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending')
    APPROVED = 'APPROVED', _('Approved')
    ACTIVE = 'ACTIVE', _('Active')
    WARNING = 'WARNING', _('Warning')
    READ_ONLY = 'READ_ONLY', _('Read Only')
    SUSPENDED = 'SUSPENDED', _('Suspended')
    ARCHIVED = 'ARCHIVED', _('Archived')
    DELETED = 'DELETED', _('Deleted')

class Tenant(BaseModel, SoftDeleteModel):
    """
    Core organization representation for the multi-tenant architecture.
    """
    tenant_code = models.CharField(max_length=50, unique=True, db_index=True)
    tenant_name = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255)
    company_email = models.EmailField(null=True, blank=True)
    company_phone = models.CharField(max_length=50, null=True, blank=True)
    company_domain = models.CharField(max_length=255, unique=True, db_index=True)
    company_logo = models.URLField(null=True, blank=True)
    
    timezone = models.CharField(max_length=100, default='UTC')
    language = models.CharField(max_length=10, default='en')
    currency = models.CharField(max_length=3, default='USD')
    
    tenant_status = models.CharField(
        max_length=20, 
        choices=TenantStatus.choices, 
        default=TenantStatus.PENDING,
        db_index=True
    )
    
    owner = models.ForeignKey(
        'authentication.User', 
        on_delete=models.PROTECT,
        related_name='owned_tenants'
    )
    
    # ---- Managers ----
    objects = TenantScopedManager()
    unscoped = UnscopedManager()

    class Meta:
        db_table = 'tenants_tenant'
        verbose_name = _('Tenant')
        verbose_name_plural = _('Tenants')
        
    def __str__(self):
        return f"{self.tenant_name} ({self.tenant_code})"
