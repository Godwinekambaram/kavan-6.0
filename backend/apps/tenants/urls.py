from django.urls import path
from .views import TenantListCreateAPIView, TenantDetailAPIView, TenantFreezeAPIView

urlpatterns = [
    path('tenants/', TenantListCreateAPIView.as_view(), name='tenant-list-create'),
    path('tenants/<uuid:pk>/', TenantDetailAPIView.as_view(), name='tenant-detail'),
    path('tenants/<uuid:pk>/freeze/', TenantFreezeAPIView.as_view(), name='tenant-freeze'),
]
