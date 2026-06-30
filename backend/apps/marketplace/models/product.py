from django.db import models
from backend.common.models.base_model import BaseModel
from backend.apps.tenants.models.tenant import Tenant

class ProductStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    PUBLISHED = 'PUBLISHED', 'Published'
    ARCHIVED = 'ARCHIVED', 'Archived'

class Product(BaseModel):
    code = models.CharField(max_length=100, unique=True, help_text='e.g., crm, erp')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=32, choices=ProductStatus.choices, default=ProductStatus.DRAFT)
    
    class Meta:
        db_table = 'marketplace_products'

class ProductVersion(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='versions')
    version_string = models.CharField(max_length=50, help_text='e.g., v1.2.0')
    release_notes = models.TextField(blank=True)
    docker_image = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'marketplace_product_versions'
        unique_together = ('product', 'version_string')

class ProductDeployment(BaseModel):
    version = models.ForeignKey(ProductVersion, on_delete=models.CASCADE)
    target_tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=32, default='PENDING') # PENDING, RUNNING, SUCCESS, FAILED
    logs = models.TextField(blank=True)

    class Meta:
        db_table = 'marketplace_product_deployments'

class TenantProduct(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    current_version = models.ForeignKey(ProductVersion, on_delete=models.CASCADE)
    status = models.CharField(max_length=32, default='INSTALLED') # INSTALLED, SUSPENDED
    license_key = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'marketplace_tenant_products'
        unique_together = ('tenant', 'product')
