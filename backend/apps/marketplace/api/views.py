from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from backend.apps.rbac.decorators import platform_permission, tenant_permission
from backend.apps.marketplace.models.product import Product, ProductVersion, TenantProduct, ProductDeployment

class PlatformProductListCreateAPIView(APIView):
    @method_decorator(platform_permission('platform:create_product'))
    def post(self, request):
        # Super Admin creates a product globally
        return Response({'success': True, 'msg': 'Product Created'})

class TenantMarketplaceAPIView(APIView):
    @method_decorator(tenant_permission('marketplace:view'))
    def get(self, request):
        # Tenant Admin views published products available for install
        return Response({'success': True, 'msg': 'Marketplace Viewed'})

class TenantProductInstallAPIView(APIView):
    @method_decorator(tenant_permission('marketplace:install'))
    def post(self, request, product_id):
        # Tenant Admin installs a product to their tenant
        return Response({'success': True, 'msg': 'Product Installed'})
