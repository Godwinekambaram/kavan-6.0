from backend.apps.rbac.models.tenant_rbac import RolePermission
from backend.apps.rbac.models.platform_rbac import PlatformRolePermission
from backend.apps.tenants.models.tenant_member import TenantMember
from backend.apps.rbac.services.rbac_cache import RBACCache
from backend.apps.rbac.services.audit_service import RBACAuditService

class RBACService:
    @staticmethod
    def _evaluate_platform_permission(user, permission_code):
        if user.platform_role == 'SUPER_ADMIN': return True
        return PlatformRolePermission.objects.filter(role=user.platform_role, permission__code=permission_code).exists()

    @staticmethod
    def _evaluate_tenant_permission(user, tenant, permission_code):
        member = TenantMember.objects.filter(user=user, tenant=tenant, status='ACTIVE').first()
        if not member: return False, None
        if member.role == 'OWNER': return True, member.role
        allowed = RolePermission.objects.filter(role=member.role, permission__code=permission_code).exists()
        return allowed, member.role

    @staticmethod
    def check_permission(user, tenant, permission_code, is_platform_request=False):
        if not user or not user.is_authenticated: return False

        # 1. Cache Check
        cached = RBACCache.get_permission(user.id, getattr(tenant, 'id', None), permission_code)
        if cached is not None: return cached

        is_allowed = False
        role_evaluated = getattr(user, 'platform_role', None) if is_platform_request else None

        # 2. Platform Permission Check
        if is_platform_request:
            if not user.platform_role:
                is_allowed = False
            else:
                is_allowed = RBACService._evaluate_platform_permission(user, permission_code)
        
        # 3. Tenant Permission Check
        else:
            if not tenant:
                is_allowed = False
            else:
                is_allowed, role_evaluated = RBACService._evaluate_tenant_permission(user, tenant, permission_code)

        # 4. Update Cache
        RBACCache.set_permission(user.id, getattr(tenant, 'id', None), permission_code, is_allowed)

        # 5. Audit Logging
        RBACAuditService.log_decision(user, tenant, role_evaluated, permission_code, is_allowed)

        return is_allowed
