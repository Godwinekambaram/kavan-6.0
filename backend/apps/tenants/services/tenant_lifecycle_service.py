from django.utils import timezone
from backend.apps.tenants.models.tenant import Tenant

class TenantLifecycleService:
    @classmethod
    def onboard_tenant(cls, tenant_code, company_name):
        # Create tenant
        tenant = Tenant.objects.create(
            tenant_code=tenant_code,
            company_name=company_name,
            tenant_status='ACTIVE'
        )
        return tenant
        
    @classmethod
    def activate_tenant(cls, tenant):
        if tenant.tenant_status == 'ACTIVE':
            raise ValueError('Tenant is already active')
        tenant.tenant_status = 'ACTIVE'
        tenant.save(update_fields=['tenant_status', 'updated_at'])
        # trigger_audit('TENANT_ACTIVATED', tenant)
        
    @classmethod
    def suspend_tenant(cls, tenant, reason=''):
        tenant.tenant_status = 'SUSPENDED'
        tenant.save(update_fields=['tenant_status', 'updated_at'])
        # trigger_audit('TENANT_SUSPENDED', tenant, reason)

    @classmethod
    def freeze_tenant(cls, tenant):
        tenant.tenant_status = 'FROZEN'
        tenant.save(update_fields=['tenant_status', 'updated_at'])

    @classmethod
    def archive_tenant(cls, tenant):
        tenant.tenant_status = 'ARCHIVED'
        tenant.save(update_fields=['tenant_status', 'updated_at'])

    @classmethod
    def restore_tenant(cls, tenant):
        if tenant.tenant_status != 'ARCHIVED':
            raise ValueError('Only archived tenants can be restored')
        tenant.tenant_status = 'ACTIVE'
        tenant.save(update_fields=['tenant_status', 'updated_at'])

    @classmethod
    def delete_tenant(cls, tenant):
        tenant.delete() # Triggers SoftDeleteModel
