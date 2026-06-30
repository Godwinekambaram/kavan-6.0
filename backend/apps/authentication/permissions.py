from rest_framework.permissions import BasePermission

class IsAuthenticatedUser(BasePermission):
    """
    Allows access only to authenticated users (bypasses Django's default session check in favor of our JWT middleware).
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

class IsVerifiedUser(BasePermission):
    """
    Allows access only if the user's email has been verified.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and getattr(request.user, 'is_verified', False))

class IsMFAAuthenticated(BasePermission):
    """
    Allows access only if the JWT payload indicates MFA was successfully completed.
    Requires the AuthenticationValidationMiddleware to attach token claims to the request.
    """
    def has_permission(self, request, view):
        # Implementation assumes request.auth contains the JWT payload
        return bool(request.user and request.user.is_authenticated and request.auth and request.auth.get('mfa_verified', False))
