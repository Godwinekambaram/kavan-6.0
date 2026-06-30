from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from backend.apps.rbac.services.rbac_service import RBACService

class RBACMiddleware(MiddlewareMixin):
    # This middleware acts as a fail-safe, but explicit route protection should happen via Decorators/Classes
    # in the DRF views. A generic RBAC middleware is risky unless permissions are explicitly tied to URL paths.
    # Therefore, this middleware enforces that the user has AT LEAST basic platform access OR is part of the tenant
    # before even reaching the view controllers.
    
    def process_request(self, request):
        if request.path.startswith('/api/v1/platform/'):
            # Must have a platform role
            if not getattr(request.user, 'platform_role', None):
                return JsonResponse({'error': 'Platform Access Denied'}, status=403)
                
        elif request.path.startswith('/api/v1/tenant/'):
            tenant = getattr(request, 'tenant', None)
            if not tenant:
                return JsonResponse({'error': 'Tenant context missing'}, status=403)
