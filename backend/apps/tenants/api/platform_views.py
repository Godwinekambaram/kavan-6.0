from rest_framework.views import APIView
from rest_framework.response import Response
from backend.apps.tenants.permissions import IsPlatformAdmin
from backend.apps.tenants.models.tenant import Tenant
from backend.apps.tenants.serializers import TenantSerializer

class PlatformTenantListAPIView(APIView):
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request):
        # Platform Admins bypass TenantScopedManager by using the unscoped manager
        # Provided the Tenant model has unscoped_objects = UnscopedManager() defined, 
        # or we fallback to the default private base manager _base_manager
        tenants = Tenant.unscoped.all() 
        serializer = TenantSerializer(tenants, many=True)
        return Response({'success': True, 'data': serializer.data})
