from functools import wraps
from rest_framework.exceptions import PermissionDenied
from backend.apps.rbac.services.rbac_service import RBACService

def platform_permission(permission_code):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not RBACService.check_permission(request.user, None, permission_code, is_platform_request=True):
                raise PermissionDenied('You do not have the required platform permission.')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def tenant_permission(permission_code):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            tenant = getattr(request, 'tenant', None)
            if not tenant:
                raise PermissionDenied('No active tenant context found.')
            if not RBACService.check_permission(request.user, tenant, permission_code, is_platform_request=False):
                raise PermissionDenied('You do not have the required tenant permission.')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
