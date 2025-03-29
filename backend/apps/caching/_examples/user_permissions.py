from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import time
import logging

from apps.caching.utils.redis_cache import get_or_set_cache, invalidate_cache

logger = logging.getLogger(__name__)


def get_user_permissions(user_id):
    """
    Get the permissions for a user.
    
    This is a common operation that can be expensive if it involves
    complex permission calculations or multiple database queries.
    Caching this can significantly improve performance for authenticated routes.
    """
    # Create a cache key specific to this user's permissions
    cache_key = f"user_permissions:{user_id}"
    
    # Define the function to get permissions if not cached
    def fetch_permissions():
        logger.info(f"Computing permissions for user {user_id}")
        
        # Simulate a complex permission calculation
        # In a real app, this might involve multiple queries to user groups,
        # roles, and permission tables
        time.sleep(1.5)  # Simulate slow operation
        
        # Mock permissions data
        permissions = {
            "can_view_reports": True,
            "can_edit_users": False,
            "can_delete_records": False,
            "can_approve_orders": True,
            "can_access_admin": False,
            # Add more permissions as needed
        }
        
        return permissions
    
    # Get from cache or compute and cache for 1 hour
    # Permissions typically don't change often, so a longer cache time is reasonable
    return get_or_set_cache(cache_key, fetch_permissions, timeout=60*60)


def invalidate_user_permissions(user_id):
    """
    Invalidate the cached permissions for a user.
    
    This should be called whenever a user's permissions change,
    such as when they are added to or removed from a group.
    """
    cache_key = f"user_permissions:{user_id}"
    return invalidate_cache(cache_key)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_permission(request):
    """
    Check if the current user has a specific permission.
    
    This demonstrates how to use cached permissions in a view.
    """
    # Get the permission to check from the query parameters
    permission = request.query_params.get('permission', 'can_view_reports')
    
    # Get the user's ID
    user_id = request.user.id
    
    # Get the user's cached permissions
    permissions = get_user_permissions(user_id)
    
    # Check if the user has the requested permission
    has_permission = permissions.get(permission, False)
    
    return Response({
        "user_id": user_id,
        "permission": permission,
        "has_permission": has_permission,
        "all_permissions": permissions
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_permissions(request):
    """
    Update a user's permissions and invalidate their permission cache.
    
    This demonstrates how to invalidate a cache when the underlying data changes.
    """
    # In a real app, you would update the user's permissions in the database here
    # For this example, we'll just invalidate the cache
    
    user_id = request.user.id
    
    # Invalidate the user's permission cache
    invalidate_user_permissions(user_id)
    
    return Response({
        "message": f"Permissions cache for user {user_id} has been invalidated",
        "success": True
    })
