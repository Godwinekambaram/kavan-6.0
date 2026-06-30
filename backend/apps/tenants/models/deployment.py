from django.db import models
from backend.common.models.base_model import BaseModel

class Deployment(BaseModel):
    tenant = models.OneToOneField('tenants.Tenant', on_delete=models.CASCADE, related_name='deployment')
    deployment_mode = models.CharField(max_length=50, default='CLOUD')
    region = models.CharField(max_length=100)
    server_ip = models.GenericIPAddressField(null=True, blank=True)
    version = models.CharField(max_length=50)
    health_status = models.CharField(max_length=50, default='HEALTHY')
    
    class Meta:
        db_table = 'tenants_deployment'
