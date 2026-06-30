from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

class KAVANException(Exception):
    """Base class for all enterprise exceptions."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "ERR_000"

    def __init__(self, message=None):
        super().__init__(message)
        self.message = message

class AuthenticationException(KAVANException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "AUTH_001"

class TokenException(KAVANException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "AUTH_002"

class OAuthException(KAVANException):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "AUTH_003"

class MFAException(KAVANException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "AUTH_004"

class ValidationException(KAVANException):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "VAL_001"

def enterprise_exception_handler(exc, context):
    """
    Standardizes all API responses into a consistent JSON envelope.
    """
    response = exception_handler(exc, context)

    if isinstance(exc, KAVANException):
        return Response({
            "success": False,
            "error_code": exc.error_code,
            "message": exc.message,
            "data": {},
            "errors": []
        }, status=exc.status_code)

    if response is not None:
        # Normalize DRF default exceptions
        return Response({
            "success": False,
            "error_code": "API_ERR",
            "message": "A validation or request error occurred.",
            "data": {},
            "errors": response.data
        }, status=response.status_code)

    # Unhandled Exception
    logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True)
    return Response({
        "success": False,
        "error_code": "SYS_001",
        "message": "An unexpected system error occurred.",
        "data": {},
        "errors": []
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
