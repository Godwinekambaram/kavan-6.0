from django.db import models
from backend.common.models.base_model import BaseModel

class TenantSettings(BaseModel):
    tenant = models.OneToOneField('tenants.Tenant', on_delete=models.CASCADE, related_name='settings')
    smtp_host = models.CharField(max_length=255, null=True, blank=True)
    brand_color = models.CharField(max_length=7, default='#000000')
    theme = models.CharField(max_length=50, default='light')
    password_policy = models.JSONField(default=dict)
    timezone = models.CharField(max_length=100, default='UTC')
    
    class Meta:
        db_table = 'tenants_tenantsettings'
