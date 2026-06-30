from rest_framework.permissions import BasePermission
from backend.apps.tenants.models.tenant_member import TenantMember

class IsTenantOwner(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated or not hasattr(request, 'tenant') or not request.tenant:
            return False
        member = TenantMember.objects.filter(user=request.user, tenant=request.tenant).first()
        return bool(member and member.role == 'OWNER' and member.status == 'ACTIVE')

class IsTenantAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated or not hasattr(request, 'tenant') or not request.tenant:
            return False
        member = TenantMember.objects.filter(user=request.user, tenant=request.tenant).first()
        return bool(member and member.role in ['OWNER', 'ADMIN'] and member.status == 'ACTIVE')

class IsTenantDeveloper(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated or not hasattr(request, 'tenant') or not request.tenant:
            return False
        member = TenantMember.objects.filter(user=request.user, tenant=request.tenant).first()
        return bool(member and member.role in ['OWNER', 'ADMIN', 'DEVELOPER'] and member.status == 'ACTIVE')

class CanManageSubscription(IsTenantOwner):
    pass

class IsPlatformAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and getattr(request.user, 'platform_role', None) == 'SUPER_ADMIN')
