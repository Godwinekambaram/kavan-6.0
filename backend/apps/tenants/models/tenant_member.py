from django.db import models
from backend.common.models.base_model import BaseModel
from django.utils.translation import gettext_lazy as _

class MemberRole(models.TextChoices):
    OWNER = 'OWNER', _('Owner')
    ADMIN = 'ADMIN', _('Admin')
    DEVELOPER = 'DEVELOPER', _('Developer')
    MEMBER = 'MEMBER', _('Member')

class MemberStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending')
    ACTIVE = 'ACTIVE', _('Active')
    SUSPENDED = 'SUSPENDED', _('Suspended')

class TenantMember(BaseModel):
    """
    Associates a User with a Tenant. Prepares the system for Layer 4 RBAC.
    """
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='members'
    )
    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='tenant_memberships'
    )
    role = models.CharField(
        max_length=50,
        choices=MemberRole.choices,
        default=MemberRole.MEMBER
    )
    status = models.CharField(
        max_length=20,
        choices=MemberStatus.choices,
        default=MemberStatus.PENDING
    )
    department = models.CharField(max_length=100, null=True, blank=True)
    joined_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'tenants_tenantmember'
        unique_together = ('tenant', 'user')
        
    def __str__(self):
        return f"{self.user.email} - {self.tenant.tenant_name} ({self.role})"
