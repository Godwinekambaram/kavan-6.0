from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated

from backend.apps.authentication.serializers.auth import (
    LoginSerializer, RegisterSerializer, RefreshTokenSerializer,
    ForgotPasswordSerializer, ResetPasswordSerializer, VerifyEmailSerializer
)
from backend.apps.authentication.services.auth_service import AuthService, AuthenticationException
from backend.apps.authentication.services.token_service import TokenService, TokenException
from backend.common.responses.standard_response import StandardResponse

class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return StandardResponse.error("Validation Failed", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        
        try:
            data = AuthService.login(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
                request_meta=request.META
            )
            return StandardResponse.success("Login successful", data=data)
        except AuthenticationException as e:
            return StandardResponse.error(str(e), status_code=status.HTTP_401_UNAUTHORIZED)


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return StandardResponse.error("Validation Failed", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = AuthService.register(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
                first_name=serializer.validated_data.get('first_name', ''),
                last_name=serializer.validated_data.get('last_name', ''),
                request_meta=request.META
            )
            return StandardResponse.success("Registration successful. Please verify your email.", status_code=status.HTTP_201_CREATED)
        except AuthenticationException as e:
            return StandardResponse.error(str(e), status_code=status.HTTP_400_BAD_REQUEST)


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        access_token = auth_header.split(' ')[1] if ' ' in auth_header else ''
        refresh_token = request.data.get('refresh_token', '')

        AuthService.logout(
            user=request.user,
            access_token=access_token,
            refresh_token_raw=refresh_token,
            request_meta=request.META
        )
        return StandardResponse.success("Logout successful")


class RefreshAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return StandardResponse.error("Validation Failed", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

        try:
            access, refresh, expires_at, user = TokenService.rotate_refresh_token(
                raw_refresh_token=serializer.validated_data['refresh_token'],
                ip_address=request.META.get("REMOTE_ADDR")
            )
            return StandardResponse.success("Token refreshed successfully", data={
                "access_token": access,
                "refresh_token": refresh,
                "expires_at": expires_at.isoformat()
            })
        except TokenException as e:
            return StandardResponse.error(str(e), status_code=status.HTTP_401_UNAUTHORIZED)


class ForgotPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return StandardResponse.error("Validation Failed", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
            
        AuthService.forgot_password(
            email=serializer.validated_data['email'],
            request_meta=request.META
        )
        # Always return success to prevent email enumeration
        return StandardResponse.success("If the email exists, a reset link has been sent.")


class ResetPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return StandardResponse.error("Validation Failed", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

        try:
            AuthService.reset_password(
                token=serializer.validated_data['token'],
                new_password=serializer.validated_data['password'],
                request_meta=request.META
            )
            return StandardResponse.success("Password reset successfully.")
        except AuthenticationException as e:
            return StandardResponse.error(str(e), status_code=status.HTTP_400_BAD_REQUEST)


class VerifyEmailAPIView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return StandardResponse.error("Validation Failed", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
            
        # Call AuthService (stubbed logic for now)
        return StandardResponse.success("Email verified successfully.")
