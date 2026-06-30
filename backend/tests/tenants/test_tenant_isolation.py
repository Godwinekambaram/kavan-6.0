import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from backend.apps.tenants.models.tenant import Tenant
from backend.apps.tenants.models.tenant_member import TenantMember
from backend.apps.authentication.models import User
from rest_framework_simplejwt.tokens import RefreshToken

@pytest.mark.django_db
class TestTenantIsolation:
    def setup_method(self):
        self.client = APIClient()
        
        # Create Tenant A
        self.tenant_a = Tenant.objects.create(tenant_code='tenant_a', company_domain='companya.com', company_name='Company A')
        self.user_a = User.objects.create_user(email='user_a@companya.com', password='StrongPassword123!')
        
        # Link user_a to tenant_a
        TenantMember.objects.create(tenant=self.tenant_a, user=self.user_a, role='OWNER', status='ACTIVE')
        
        # Create Tenant B
        self.tenant_b = Tenant.objects.create(tenant_code='tenant_b', company_domain='companyb.com', company_name='Company B')
        self.user_b = User.objects.create_user(email='user_b@companyb.com', password='StrongPassword123!')
        
        # Link user_b to tenant_b
        TenantMember.objects.create(tenant=self.tenant_b, user=self.user_b, role='OWNER', status='ACTIVE')

    def _get_jwt_for_user(self, user):
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def test_tenant_a_can_access_tenant_a_data(self):
        token = self._get_jwt_for_user(self.user_a)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Resolving via subdomain
        response = self.client.get(reverse('tenant-list-create'), HTTP_HOST='tenant_a.lvh.me')
        assert response.status_code == 200
        assert len(response.data['data']) == 1
        assert response.data['data'][0]['id'] == str(self.tenant_a.id)

    def test_tenant_a_cannot_access_tenant_b_data(self):
        token = self._get_jwt_for_user(self.user_a)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Attempt to access Tenant B via Tenant B's subdomain
        response = self.client.get(reverse('tenant-detail', kwargs={'pk': self.tenant_b.pk}), HTTP_HOST='tenant_b.lvh.me')
        assert response.status_code in [403, 404]

    def test_custom_domain_resolution(self):
        token = self._get_jwt_for_user(self.user_a)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Resolving via custom domain
        response = self.client.get(reverse('tenant-list-create'), HTTP_HOST='companya.com')
        assert response.status_code == 200
        assert len(response.data['data']) == 1
        assert response.data['data'][0]['id'] == str(self.tenant_a.id)
