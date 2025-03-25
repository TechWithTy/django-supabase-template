from typing import Any, Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
import logging

logger = logging.getLogger('apps.authentication')

class SupabaseJWTMiddleware:
    """
    Middleware to validate Supabase JWT tokens.
    
    This middleware checks for a valid JWT token in the Authorization header
    and validates it against the Supabase JWT secret. If valid, it adds the
    user information to the request for use in views.
    """
    
    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response
        self.jwt_secret = settings.SUPABASE_JWT_SECRET
        
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Skip JWT validation for certain paths
        exempt_paths = [
            '/admin/', 
            '/metrics/', 
            '/api/health/',
            '/api/login/',
            '/api/register/',
        ]
        
        path = request.path
        if any(path.startswith(exempt_path) for exempt_path in exempt_paths):
            return self.get_response(request)
        
        # Get the Authorization header
        auth_header = request.headers.get('Authorization', '')
        
        # If no Authorization header, continue to the view
        # (the view's permission classes will handle unauthorized access)
        if not auth_header.startswith('Bearer '):
            return self.get_response(request)
        
        # Extract the token
        token = auth_header.split(' ')[1]
        
        try:
            # Decode and verify the token
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=['HS256'],
                options={'verify_signature': True}
            )
            
            # Add user info to request
            request.supabase_user = payload.get('sub')
            request.supabase_claims = payload.get('claims', {})
            request.supabase_roles = payload.get('roles', [])
            
            # Log successful authentication
            logger.info(f"User {request.supabase_user} authenticated successfully")
            
        except ExpiredSignatureError:
            logger.warning(f"Expired JWT token received")
            return JsonResponse(
                {"error": "Token expired"},
                status=401
            )
            
        except InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            return JsonResponse(
                {"error": "Invalid authentication token"},
                status=401
            )
            
        except Exception as e:
            logger.error(f"JWT validation error: {str(e)}")
            return JsonResponse(
                {"error": "Authentication error"},
                status=401
            )
        
        return self.get_response(request)
