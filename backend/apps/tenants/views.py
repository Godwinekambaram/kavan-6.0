from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from backend.apps.tenants.services.tenant_lifecycle_service import TenantLifecycleService
from backend.apps.tenants.services.tenant_context_service import TenantContextService
from backend.apps.tenants.repositories.repositories import TenantRepository
from backend.apps.tenants.serializers import TenantSerializer
from backend.apps.tenants.permissions import IsTenantAdmin

class TenantListCreateAPIView(APIView):
    permission_classes = [IsTenantAdmin]

    def get(self, request):
        tenants = TenantRepository.get_queryset()
        serializer = TenantSerializer(tenants, many=True)
        return Response({'success': True, 'data': serializer.data})

    def post(self, request):
        serializer = TenantSerializer(data=request.data)
        if serializer.is_valid():
            tenant = TenantLifecycleService.onboard_tenant(
                tenant_code=serializer.validated_data.get('tenant_code'),
                company_name=serializer.validated_data.get('company_name')
            )
            return Response({'success': True, 'data': TenantSerializer(tenant).data}, status=status.HTTP_201_CREATED)
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class TenantDetailAPIView(APIView):
    permission_classes = [IsTenantAdmin]

    def get(self, request, pk):
        tenant = TenantRepository.get_by_id(pk)
        if not tenant: return Response(status=404)
        return Response({'success': True, 'data': TenantSerializer(tenant).data})

class TenantFreezeAPIView(APIView):
    permission_classes = [IsTenantAdmin]

    def post(self, request, pk):
        tenant = TenantRepository.get_by_id(pk)
        if not tenant: return Response(status=404)
        TenantLifecycleService.freeze_tenant(tenant)
        return Response({'success': True, 'message': 'Tenant frozen'})

from django.utils.decorators import method_decorator
from backend.apps.rbac.decorators import platform_permission, tenant_permission

class SecureTenantCreateAPIView(APIView):
    @method_decorator(platform_permission('platform:create_tenant'))
    def post(self, request):
        return Response({'success': True})

class SecureUserDeleteAPIView(APIView):
    @method_decorator(tenant_permission('users:delete'))
    def delete(self, request, user_id):
        return Response({'success': True})
