from django.db import models
import uuid

class PlatformPermission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=100, unique=True, help_text='e.g., platform:suspend_tenant')
    description = models.CharField(max_length=255)

    class Meta:
        db_table = 'rbac_platform_permissions'

class PlatformRolePermission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Refers to User.PlatformRole choices (SUPER_ADMIN, etc)
    role = models.CharField(max_length=32, db_index=True)
    permission = models.ForeignKey(PlatformPermission, on_delete=models.CASCADE)

    class Meta:
        db_table = 'rbac_platform_role_permissions'
        unique_together = ('role', 'permission')
