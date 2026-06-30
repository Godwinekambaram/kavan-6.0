from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from backend.apps.tenants.utils.domain_resolver import DomainResolver
from backend.apps.tenants.services.tenant_context_service import TenantContextService
from backend.apps.tenants.models.tenant import Tenant

class TenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        TenantContextService.clear()
        
        host = request.get_host()
        resolved_domain = DomainResolver.resolve(host)
        
        if resolved_domain:
            # First try matching tenant_code (for subdomains), then company_domain (for custom domains)
            tenant = Tenant.objects.filter(tenant_code=resolved_domain).first()
            if not tenant:
                tenant = Tenant.objects.filter(company_domain=resolved_domain).first()
                
            if tenant:
                if tenant.tenant_status in ['SUSPENDED', 'ARCHIVED']:
                    return JsonResponse({'error': 'Tenant suspended or archived'}, status=403)
                    
                request.tenant = tenant
                
                # Fetch related data if it exists, without crashing if it doesn't
                request.subscription = getattr(tenant, 'subscription', None)
                request.deployment = getattr(tenant, 'deployment', None)
                
                TenantContextService.set_current_tenant(tenant)
                return None
                
        # If we reach here, no tenant was found or resolved
        request.tenant = None

    def process_response(self, request, response):
        TenantContextService.clear()
        return response
        
    def process_exception(self, request, exception):
        TenantContextService.clear()
