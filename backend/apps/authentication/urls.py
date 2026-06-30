from django.urls import path
from backend.apps.authentication.views import (
    LoginAPIView, RegisterAPIView, LogoutAPIView, RefreshAPIView,
    ForgotPasswordAPIView, ResetPasswordAPIView, VerifyEmailAPIView
)

app_name = 'authentication'

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='login'),
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    path('refresh/', RefreshAPIView.as_view(), name='refresh'),
    path('forgot-password/', ForgotPasswordAPIView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordAPIView.as_view(), name='reset-password'),
    path('verify-email/', VerifyEmailAPIView.as_view(), name='verify-email'),
]
