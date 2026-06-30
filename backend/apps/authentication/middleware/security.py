import re
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from backend.apps.authentication.services.token_service import TokenService, TokenException
from backend.apps.authentication.models import User

class AuthenticationValidationMiddleware(MiddlewareMixin):
    """
    Enterprise middleware ensuring valid JWTs and executing Redis Blacklist checks 
    before the request ever reaches the views.
    """
    
    def process_request(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                payload = TokenService.validate_access_token(token)
                
                # Attach user to request
                user_id = payload.get('sub')
                if user_id:
                    # Cache the user or get from DB
                    user = User.objects.filter(id=user_id).first()
                    if user:
                        request.user = user
                        
            except TokenException as e:
                return JsonResponse({
                    "success": False,
                    "error": {
                        "code": "token_invalid",
                        "message": str(e)
                    }
                }, status=401)
                
        return None

class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Applies enterprise security headers to all outgoing responses.
    """
    def process_response(self, request, response):
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        response['X-Frame-Options'] = 'DENY'
        response['Content-Security-Policy'] = "default-src 'self'"
        response['X-Content-Type-Options'] = 'nosniff'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response
