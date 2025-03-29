import logging
from typing import Dict, Any
from datetime import datetime

from django.db import connection
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request: Request) -> Response:
    """
    Health check endpoint for monitoring and container orchestration.
    
    This endpoint checks:
    1. API is responsive
    2. Database connection is working
    3. Redis connection is working (if configured)
    
    Returns HTTP 200 if all systems are operational, HTTP 503 otherwise.
    """
    health_status: Dict[str, Any] = {
        "status": "ok",
        "api": True,
        "database": False,
        "redis": False,
        "version": getattr(settings, 'APP_VERSION', 'dev'),
        "timestamp": datetime.now().isoformat(),
    }
    
    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            health_status["database"] = True
    except Exception as e:
        logger.error(f"Health check - Database error: {str(e)}")
        health_status["status"] = "degraded"
    
    # Check Redis connection if configured
    if hasattr(settings, 'REDIS_URL') and settings.REDIS_URL:
        try:
            import redis
            redis_client = redis.from_url(settings.REDIS_URL)
            redis_client.ping()
            health_status["redis"] = True
        except Exception as e:
            logger.error(f"Health check - Redis error: {str(e)}")
            health_status["status"] = "degraded"
    
    status_code = 200 if health_status["status"] == "ok" else 503
    return Response(health_status, status=status_code)

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check_supabase(request: Request) -> Response:
    """
    Health check endpoint for Supabase connection.
    
    This endpoint checks:
    1. API is responsive
    2. Supabase connection is working
    
    Returns HTTP 200 if Supabase is operational, HTTP 503 otherwise.
    """
    health_status: Dict[str, Any] = {
        "status": "ok",
        "version": getattr(settings, 'APP_VERSION', 'dev'),
        "timestamp": datetime.now().isoformat(),
    }
    
    # Check Supabase connection
    try:
        # Import here to avoid circular imports
        from apps.supabase_home.init import get_supabase_client
        
        # Get Supabase client and perform a simple operation
        supabase = get_supabase_client()
        # Just checking if we can get the client without errors
        if supabase:
            health_status["supabase_connected"] = True
        else:
            health_status["supabase_connected"] = False
            health_status["status"] = "degraded"
    except Exception as e:
        logger.error(f"Health check - Supabase error: {str(e)}")
        health_status["supabase_connected"] = False
        health_status["status"] = "degraded"
    
    status_code = 200 if health_status["status"] == "ok" else 503
    return Response(health_status, status=status_code)
