from django.db.models.signals import post_save
from django.dispatch import receiver
from backend.apps.tenants.models.tenant import Tenant
from backend.apps.tenants.models.subscription import Subscription
from backend.apps.tenants.models.tenant_settings import TenantSettings
from backend.apps.tenants.models.tenant_metrics import TenantMetrics
from backend.apps.tenants.models.tenant_backup import TenantBackup
from backend.apps.tenants.models.deployment import Deployment
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Tenant)
def initialize_tenant_scaffolding(sender, instance, created, **kwargs):
    if created:
        logger.info(f'Tenant Created: {instance.tenant_code}. Initializing scaffolding...')
        
        # 1. Create Default Subscription
        Subscription.objects.create(
            tenant=instance,
            license_key=f'FREE-{instance.id}',
            plan='FREE_TIER',
            user_quota=10,
            storage_quota_mb=1024,
            api_quota=10000
        )
        
        # 2. Create Default Settings
        TenantSettings.objects.create(
            tenant=instance,
            brand_color='#0052CC',
            theme='light',
            timezone='UTC'
        )
        
        # 3. Create Default Metrics
        TenantMetrics.objects.create(
            tenant=instance
        )
        
        # 4. Create Initial Backup Metadata
        TenantBackup.objects.create(
            tenant=instance,
            backup_status='INITIALIZED',
            encryption_status=True
        )
        
        # 5. Create Default Deployment
        Deployment.objects.create(
            tenant=instance,
            deployment_mode='CLOUD',
            region='us-east-1',
            version='v5.2.0'
        )
        
        logger.info(f'Scaffolding complete for Tenant: {instance.tenant_code}')

        # 6. Default Admin Assignment (Handled by View, or if we have user context here, assign it)
        # Note: In post_save of Tenant, we don't naturally have the User. 
        # Typically the onboard_tenant service method creates the TenantMember immediately after saving the Tenant.
        # But we ensure RBAC is ready.
