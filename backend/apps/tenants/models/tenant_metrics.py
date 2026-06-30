from django.db import models
from backend.common.models.base_model import BaseModel

class TenantMetrics(BaseModel):
    tenant = models.OneToOneField('tenants.Tenant', on_delete=models.CASCADE, related_name='metrics')
    active_users = models.IntegerField(default=0)
    storage_used_mb = models.FloatField(default=0.0)
    api_calls = models.BigIntegerField(default=0)
    cpu_usage_percent = models.FloatField(default=0.0)
    ram_usage_mb = models.FloatField(default=0.0)
    threat_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'tenants_tenantmetrics'
