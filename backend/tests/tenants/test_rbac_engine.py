import pytest
from backend.apps.rbac.services.rbac_service import RBACService
from backend.apps.rbac.models.tenant_rbac import TenantRole, TenantPermission, RolePermission
from backend.apps.rbac.models.platform_rbac import PlatformPermission, PlatformRolePermission
from backend.apps.tenants.models.tenant import Tenant
from backend.apps.tenants.models.tenant_member import TenantMember
from backend.apps.authentication.models import User

@pytest.mark.django_db
class TestRBACEngine:
    def setup_method(self):
        # Platform
        self.super_admin = User.objects.create_user(email='super@kavan.com', password='pw')
        self.super_admin.platform_role = 'SUPER_ADMIN'
        self.super_admin.save()
        
        self.support = User.objects.create_user(email='support@kavan.com', password='pw')
        self.support.platform_role = 'PLATFORM_SUPPORT'
        self.support.save()
        
        self.perm_suspend = PlatformPermission.objects.create(code='platform:suspend_tenant')
        self.perm_view = PlatformPermission.objects.create(code='platform:view_metrics')
        
        PlatformRolePermission.objects.create(role='PLATFORM_SUPPORT', permission=self.perm_view)
        
        # Tenant
        self.tenant = Tenant.objects.create(tenant_code='test', company_name='test')
        self.tenant_owner = User.objects.create_user(email='owner@test.com', password='pw')
        TenantMember.objects.create(tenant=self.tenant, user=self.tenant_owner, role='OWNER', status='ACTIVE')
        
        self.tenant_dev = User.objects.create_user(email='dev@test.com', password='pw')
        TenantMember.objects.create(tenant=self.tenant, user=self.tenant_dev, role='DEVELOPER', status='ACTIVE')
        
        self.perm_billing = TenantPermission.objects.create(code='billing:read')
        RolePermission.objects.create(role='DEVELOPER', permission=self.perm_billing)

    def test_platform_permissions(self):
        # Super admin has implicit all access (our logic says True if SUPER_ADMIN)
        assert RBACService.has_platform_permission(self.super_admin, 'platform:suspend_tenant') == True
        
        # Support has explicit view access, but NO suspend access
        assert RBACService.has_platform_permission(self.support, 'platform:view_metrics') == True
        assert RBACService.has_platform_permission(self.support, 'platform:suspend_tenant') == False

    def test_tenant_permissions(self):
        # Owner has implicit all access
        assert RBACService.has_tenant_permission(self.tenant_owner, self.tenant, 'billing:write') == True
        
        # Developer has explicit billing:read, but NO billing:write
        assert RBACService.has_tenant_permission(self.tenant_dev, self.tenant, 'billing:read') == True
        assert RBACService.has_tenant_permission(self.tenant_dev, self.tenant, 'billing:write') == False
