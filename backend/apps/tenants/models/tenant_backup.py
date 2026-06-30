from django.db import models
from backend.common.models.base_model import BaseModel

class TenantBackup(BaseModel):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='backups')
    backup_status = models.CharField(max_length=50, default='PENDING')
    encryption_status = models.BooleanField(default=True)
    restore_point_url = models.URLField(max_length=1024, null=True, blank=True)
    checksum = models.CharField(max_length=255, null=True, blank=True)
    last_successful_backup = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'tenants_tenantbackup'
