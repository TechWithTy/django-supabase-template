from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import time
import logging

from apps.caching.utils.redis_cache import cache_result, invalidate_cache, get_cached_result

logger = logging.getLogger(__name__)


@api_view(['GET'])
@cache_result(timeout=60 * 5)  # Cache for 5 minutes
def cached_data_example(request):
    """
    Example view that demonstrates caching an expensive operation.
    The first request will be slow, but subsequent requests will be fast.
    """
    # Simulate an expensive operation (e.g., complex database query or API call)
    logger.info("Executing expensive operation for cached_data_example")
    time.sleep(2)  # Simulate 2-second delay for the expensive operation
    
    # This result will be cached for 5 minutes
    result = {
        "data": "This is an expensive result that has been cached",
        "timestamp": time.time(),
        "cached": False  # This will be True for cached responses
    }
    
    return Response(result)


@api_view(['GET'])
def invalidate_cache_example(request):
    """
    Example view that invalidates the cache for the cached_data_example view.
    After calling this endpoint, the next request to cached_data_example will be slow again.
    """
    # Generate the same cache key that the decorator would use
    cache_key = "cached_data_example"  # Simplified for example purposes
    
    # Check if the key exists in cache before invalidating
    cached_value = get_cached_result(cache_key)
    was_cached = cached_value is not None
    
    # Invalidate the cache
    invalidate_cache(cache_key)
    
    return Response({
        "message": "Cache invalidated successfully",
        "was_cached": was_cached
    })


@api_view(['GET'])
def cache_status(request):
    """
    Example view that checks if a specific key is cached and returns its status.
    """
    cache_key = request.query_params.get('key', 'cached_data_example')
    
    # Try to get the cached value
    cached_value = get_cached_result(cache_key)
    is_cached = cached_value is not None
    
    return Response({
        "key": cache_key,
        "is_cached": is_cached,
        "value_type": type(cached_value).__name__ if is_cached else None
    })


@api_view(['GET'])
def rate_limited_example(request):
    """
    Example view that demonstrates using Redis for rate limiting.
    """
    # Get user identifier (IP address or user ID)
    user_id = getattr(request.user, 'id', None) or request.META.get('REMOTE_ADDR')
    cache_key = f"rate_limit:{user_id}"
    
    # Get current rate limit count
    count = get_cached_result(cache_key, 0)
    
    # Check if rate limit exceeded (5 requests per minute)
    limit = 5
    period = 60  # seconds
    
    if count >= limit:
        return Response({
            "error": "Rate limit exceeded. Try again later.",
            "retry_after": period
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)
    
    # Increment counter or set initial value with expiration
    from django.core.cache import cache
    if count == 0:
        cache.set(cache_key, 1, period)
    else:
        cache.incr(cache_key)
    
    # Process the request
    return Response({
        "message": "Request processed successfully",
        "requests_remaining": limit - (count + 1)
    })
