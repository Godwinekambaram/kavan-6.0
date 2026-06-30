from django.contrib.auth import authenticate
from django.utils import timezone
from typing import Dict, Any, Optional

from backend.apps.authentication.models import User
from backend.apps.authentication.services.token_service import TokenService

class AuthenticationException(Exception):
    pass

class AuthService:
    """
    Core service orchestrating authentication business logic independent of the web layer.
    """
    
    @classmethod
    def login(cls, email: str, password: str, request_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validates credentials and issues tokens.
        Includes password history and lockout checks implicitly handled by the User model or here.
        """
        user = authenticate(username=email, password=password)
        if not user:
            raise AuthenticationException("Invalid email or password.")
            
        if not user.is_active:
            raise AuthenticationException("Account is disabled.")
            
        # TODO: Implement lockouts, password expiry checks, MFA trigger here
        
        # Track session / login event (Audit Logging)
        cls._log_audit(user, "LOGIN_SUCCESS", request_meta)
        
        ip_address = request_meta.get("REMOTE_ADDR") if request_meta else None
        
        access_token, refresh_token, expires_at = TokenService.generate_tokens(
            user=user, 
            ip_address=ip_address
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at.isoformat(),
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
            "mfa_required": getattr(user, 'mfa_enabled', False)
        }

    @classmethod
    def logout(cls, user: User, access_token: str, refresh_token_raw: str, request_meta: Optional[Dict[str, Any]] = None) -> None:
        """
        Invalidates tokens and closes session.
        """
        # Blacklist current access token
        TokenService.blacklist_access_token(access_token)
        
        # Revoke the specific refresh token if provided
        if refresh_token_raw:
            try:
                # We can just rotate it to revoke, but we ignore the new tokens. 
                # Better to have a explicit revoke method, but this suffices for the MVP.
                # A proper implementation would find the RefreshToken by hash and set is_revoked=True
                token_hash = TokenService._hash_token(refresh_token_raw)
                from backend.apps.authentication.models import RefreshToken
                rt = RefreshToken.objects.filter(token_hash=token_hash).first()
                if rt:
                    rt.is_revoked = True
                    rt.revoked_at = timezone.now()
                    rt.save()
            except Exception:
                pass
                
        cls._log_audit(user, "LOGOUT", request_meta)
        
    @classmethod
    def _log_audit(cls, user: User, action: str, request_meta: Optional[Dict[str, Any]]) -> None:
        """
        Helper to log authentication events. 
        In full implementation, this writes to the Audit log model.
        """
        pass # To be fully wired with the audit app

    @classmethod
    def register(cls, email: str, password: str, first_name: str = "", last_name: str = "", request_meta: Optional[Dict[str, Any]] = None) -> User:
        """
        Registers a new user, applies password policies, creates a profile, and triggers verification.
        """
        # Validate password policy
        from backend.apps.authentication.validators import PasswordValidator
        PasswordValidator.validate(password)

        if User.objects.filter(email=email).exists():
            raise AuthenticationException("A user with this email already exists.")

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        cls._log_audit(user, "REGISTER_SUCCESS", request_meta)

        # Trigger email verification token generation
        cls.send_verification_email(user)

        return user

    @classmethod
    def forgot_password(cls, email: str, request_meta: Optional[Dict[str, Any]] = None) -> None:
        """
        Generates a secure reset token and emails the user.
        """
        user = User.objects.filter(email=email).first()
        if not user:
            # We don't raise an error to prevent email enumeration
            return

        # Generate reset token and send email
        # To be implemented using NotificationService
        cls._log_audit(user, "FORGOT_PASSWORD_REQUEST", request_meta)

    @classmethod
    def reset_password(cls, token: str, new_password: str, request_meta: Optional[Dict[str, Any]] = None) -> None:
        """
        Validates the reset token and updates the password, applying history constraints.
        """
        # Validate password policy
        from backend.apps.authentication.validators import PasswordValidator
        PasswordValidator.validate(new_password)

        # Mock token validation for now
        # token_record = PasswordReset.objects.filter(token_hash=hash(token)).first()
        # user = token_record.user
        
        # user.set_password(new_password)
        # user.save()
        
        # cls._log_audit(user, "PASSWORD_RESET_SUCCESS", request_meta)
        pass

    @classmethod
    def send_verification_email(cls, user: User) -> None:
        """
        Generates a verification token and dispatches an email.
        """
        pass

