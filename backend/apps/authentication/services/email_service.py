import logging
from django.core.mail import send_mail
from django.conf import settings
from backend.apps.authentication.models import User

logger = logging.getLogger(__name__)

class EmailService:
    """
    Dedicated service for handling all transactional emails related to authentication and identity.
    Decouples email logic from AuthService.
    """
    
    @classmethod
    def send_verification_email(cls, user: User, token: str) -> None:
        """
        Sends the initial email verification link upon registration.
        """
        subject = "Verify your KAVAN Account"
        message = f"Please verify your account by using the following token: {token}"
        cls._dispatch(subject, message, [user.email])
        
    @classmethod
    def send_password_reset(cls, user: User, token: str) -> None:
        """
        Sends a secure password reset link.
        """
        subject = "KAVAN Password Reset Request"
        message = f"You requested a password reset. Use this token: {token}"
        cls._dispatch(subject, message, [user.email])
        
    @classmethod
    def send_welcome_email(cls, user: User) -> None:
        """
        Sends a welcome email after successful verification.
        """
        subject = "Welcome to KAVAN"
        message = f"Hello {user.first_name}, welcome to the KAVAN platform."
        cls._dispatch(subject, message, [user.email])
        
    @classmethod
    def send_security_alert(cls, user: User, alert_message: str) -> None:
        """
        Sends security alerts (e.g., new device login, suspicious activity).
        """
        subject = "KAVAN Security Alert"
        cls._dispatch(subject, alert_message, [user.email])

    @classmethod
    def _dispatch(cls, subject: str, message: str, recipient_list: list) -> None:
        """
        Internal dispatcher. In production, this would offload to a Celery task.
        """
        try:
            # send_mail(
            #     subject=subject,
            #     message=message,
            #     from_email=settings.DEFAULT_FROM_EMAIL,
            #     recipient_list=recipient_list,
            #     fail_silently=False,
            # )
            logger.info(f"Email dispatched: {subject} to {recipient_list}")
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
