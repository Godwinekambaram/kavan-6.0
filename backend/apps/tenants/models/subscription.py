from django.db import models
from backend.common.models.base_model import BaseModel

class Subscription(BaseModel):
    tenant = models.OneToOneField('tenants.Tenant', on_delete=models.CASCADE, related_name='subscription')
    license_key = models.CharField(max_length=255, unique=True)
    plan = models.CharField(max_length=50)
    user_quota = models.IntegerField(default=10)
    storage_quota_mb = models.IntegerField(default=1024)
    api_quota = models.IntegerField(default=10000)
    current_users = models.IntegerField(default=0)
    current_storage_mb = models.IntegerField(default=0)
    expiry_date = models.DateTimeField(null=True, blank=True)
    renewal_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'tenants_subscription'
