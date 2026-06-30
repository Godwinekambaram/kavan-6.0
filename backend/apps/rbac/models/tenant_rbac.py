from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import uuid

class TenantRole(models.TextChoices):
    OWNER = 'OWNER', 'Owner'
    ADMIN = 'ADMIN', 'Admin'
    DEVELOPER = 'DEVELOPER', 'Developer'
    SECURITY_ANALYST = 'SECURITY_ANALYST', 'Security Analyst'
    END_USER = 'END_USER', 'End User'

class TenantPermission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=100, unique=True, help_text='e.g., billing:read')
    description = models.CharField(max_length=255)

    class Meta:
        db_table = 'rbac_tenant_permissions'

class RolePermission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=32, choices=TenantRole.choices, db_index=True)
    permission = models.ForeignKey(TenantPermission, on_delete=models.CASCADE)

    class Meta:
        db_table = 'rbac_tenant_role_permissions'
        unique_together = ('role', 'permission')

class ObjectPermission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('authentication.User', on_delete=models.CASCADE, null=True, blank=True)
    role = models.CharField(max_length=32, choices=TenantRole.choices, null=True, blank=True)
    permission = models.ForeignKey(TenantPermission, on_delete=models.CASCADE)
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        db_table = 'rbac_object_permissions'
