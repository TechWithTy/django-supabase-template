from typing import Any, Dict

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
import requests
import logging

logger = logging.getLogger('apps.authentication')

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request: Request) -> Response:
    """
    Health check endpoint to verify the API is running.
    """
    return Response({"status": "ok"}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request: Request) -> Response:
    """
    Proxy endpoint for Supabase login.
    
    This endpoint forwards login requests to Supabase and returns the JWT token.
    """
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response(
            {"error": "Email and password are required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Forward the request to Supabase
        response = requests.post(
            f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password",
            json={"email": email, "password": password},
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Content-Type": "application/json"
            }
        )
        
        # Return the Supabase response
        return Response(response.json(), status=response.status_code)
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return Response(
            {"error": "Authentication failed"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request: Request) -> Response:
    """
    Proxy endpoint for Supabase registration.
    
    This endpoint forwards registration requests to Supabase.
    """
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response(
            {"error": "Email and password are required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Forward the request to Supabase
        response = requests.post(
            f"{settings.SUPABASE_URL}/auth/v1/signup",
            json={"email": email, "password": password},
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Content-Type": "application/json"
            }
        )
        
        # Return the Supabase response
        return Response(response.json(), status=response.status_code)
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return Response(
            {"error": "Registration failed"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info(request: Request) -> Response:
    """
    Get information about the authenticated user.
    """
    user = request.user
    
    # Get user data from Supabase
    try:
        response = requests.get(
            f"{settings.SUPABASE_URL}/auth/v1/user",
            headers={
                "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}"
            }
        )
        
        supabase_user = response.json()
        
        # Combine Django user data with Supabase user data
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "supabase_id": getattr(user, 'supabase_user', None),
            "roles": getattr(user, 'supabase_roles', []),
            "claims": getattr(user, 'supabase_claims', {}),
            "supabase_data": supabase_user
        }
        
        return Response(user_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"User info error: {str(e)}")
        return Response(
            {"error": "Failed to retrieve user information"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request: Request) -> Response:
    """
    Proxy endpoint for Supabase logout.
    
    This endpoint forwards logout requests to Supabase.
    """
    try:
        # Get the JWT token from the request
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
            # Forward the request to Supabase
            response = requests.post(
                f"{settings.SUPABASE_URL}/auth/v1/logout",
                headers={
                    "apikey": settings.SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )
            
            # Return success response
            return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)
        
        return Response(
            {"error": "No authentication token provided"},
            status=status.HTTP_400_BAD_REQUEST
        )
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return Response(
            {"error": "Logout failed"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
