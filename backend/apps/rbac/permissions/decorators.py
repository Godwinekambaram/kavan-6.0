from rest_framework.permissions import BasePermission
from backend.apps.rbac.services.rbac_service import RBACService

class HasPlatformPermission:
    def __init__(self, permission_code):
        self.permission_code = permission_code

    def __call__(self):
        code = self.permission_code
        class _HasPlatformPermission(BasePermission):
            def has_permission(self, request, view):
                return bool(request.user and request.user.is_authenticated and RBACService.has_platform_permission(request.user, code))
        return _HasPlatformPermission

class HasTenantPermission:
    def __init__(self, permission_code):
        self.permission_code = permission_code

    def __call__(self):
        code = self.permission_code
        class _HasTenantPermission(BasePermission):
            def has_permission(self, request, view):
                return bool(
                    request.user and request.user.is_authenticated and 
                    hasattr(request, 'tenant') and request.tenant and 
                    RBACService.has_tenant_permission(request.user, request.tenant, code)
                )
        return _HasTenantPermission
