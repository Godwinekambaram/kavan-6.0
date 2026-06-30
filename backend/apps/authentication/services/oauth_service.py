from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from backend.apps.authentication.models import User
from backend.apps.authentication.services.auth_service import AuthenticationException

class BaseOAuthService(ABC):
    """
    Abstract base class for all Identity Providers (IdPs) in the OAuth Framework.
    """
    
    @abstractmethod
    def validate_token(self, provider_token: str) -> Dict[str, Any]:
        """
        Validates the provider-issued token and returns the normalized user profile.
        """
        pass
        
    @abstractmethod
    def authenticate(self, provider_token: str, request_meta: Optional[Dict[str, Any]] = None) -> User:
        """
        Validates the token, retrieves the profile, and returns the local KAVAN User record.
        Must handle creating or linking the user if they do not exist locally.
        """
        pass


class GoogleOAuthService(BaseOAuthService):
    """
    Concrete implementation for Google Workspace / Gmail OAuth.
    """
    
    def validate_token(self, provider_token: str) -> Dict[str, Any]:
        """
        In production, this verifies the token with Google's certs (e.g. using google-auth library).
        """
        # Mock verification logic for now
        if not provider_token or provider_token == "invalid":
            raise AuthenticationException("Invalid Google OAuth token.")
            
        return {
            "email": "user@google.com",
            "first_name": "Google",
            "last_name": "User",
            "google_id": "123456789"
        }

    def authenticate(self, provider_token: str, request_meta: Optional[Dict[str, Any]] = None) -> User:
        profile = self.validate_token(provider_token)
        email = profile["email"]
        
        # Link or create user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": profile.get("first_name", ""),
                "last_name": profile.get("last_name", ""),
            }
        )
        
        # We would log this in AuditService
        # _log_audit(user, "OAUTH_LOGIN_SUCCESS", request_meta)
        
        return user


class MicrosoftIdentityService(BaseOAuthService):
    """
    Future stub for Microsoft Entra ID integration.
    """
    def validate_token(self, provider_token: str) -> Dict[str, Any]:
        raise NotImplementedError("Microsoft Identity not yet active.")
        
    def authenticate(self, provider_token: str, request_meta: Optional[Dict[str, Any]] = None) -> User:
        raise NotImplementedError()


class LDAPService:
    """
    Future stub for legacy on-premise LDAP / Active Directory.
    Does not strictly follow OAuth flow, but acts as a provider.
    """
    pass
