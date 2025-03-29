# Redis Caching Implementation Guide

## Overview

This document provides a comprehensive guide to using the Redis caching implementation in the Django-Supabase template. The implementation follows test-driven development practices and provides utilities for efficient caching operations.

## Features

- Simple cache get/set operations
- Function result caching with automatic key generation
- Cache invalidation utilities
- Decorator-based caching for views and functions
- Configurable cache timeouts

## Basic Usage

### Direct Cache Access

For basic caching operations, you can use Django's built-in cache framework:

```python
from django.core.cache import cache

# Store a value in the cache (expires in 60 seconds)
cache.set('my_key', 'my_value', 60)

# Retrieve a value from the cache
value = cache.get('my_key')  # Returns None if key doesn't exist

# Delete a value from the cache
cache.delete('my_key')
```

## Practical Performance Optimization Examples

The following examples demonstrate how to use Redis caching for various performance optimization scenarios in your Django application.

### 1. Caching Expensive API Routes

API endpoints that perform complex operations can benefit significantly from caching. This is especially useful for endpoints that are frequently accessed but don't need real-time data.

```python
from rest_framework.decorators import api_view
from apps.caching.utils.redis_cache import cache_result

@api_view(['GET'])
@cache_result(timeout=60 * 15)  # Cache for 15 minutes
def expensive_api_example(request):
    """Example of caching an expensive API route."""
    # Expensive operation here (e.g., complex calculations, multiple DB queries)
    time.sleep(2)  # Simulating expensive operation
    
    result = {
        "data": [...],  # Your expensive-to-compute data
        "metadata": {...}
    }
    
    return Response(result)
```

**Benefits:**
- Reduces server load during traffic spikes
- Improves response times for complex API endpoints
- Decreases database load for read-heavy operations

### 2. Caching Database Query Results

Complex database queries with joins and aggregations can be expensive. Caching these results can significantly improve performance.

```python
from apps.caching.utils.redis_cache import get_or_set_cache

def get_user_order_stats(user_id):
    """Get statistics about a user's orders with caching."""
    cache_key = f"user_order_stats:{user_id}"
    
    def get_stats():
        # Complex query with joins and aggregations
        return Order.objects\
            .filter(user_id=user_id)\
            .annotate(
                order_count=Count('id'),
                total_spent=Sum('total'),
                avg_order_value=Avg('total')
            )\
            .values('order_count', 'total_spent', 'avg_order_value')\
            .first()
    
    # Get from cache or compute and cache for 1 hour
    return get_or_set_cache(cache_key, get_stats, timeout=60*60)
```

**Benefits:**
- Reduces database load for complex queries
- Improves response times for reports and dashboards
- Allows for efficient handling of expensive aggregations

### 3. Caching User Permissions

User permission checks can involve complex calculations and multiple database queries. Caching permissions can improve performance for authenticated routes.

```python
def get_user_permissions(user_id):
    """Get the permissions for a user with caching."""
    cache_key = f"user_permissions:{user_id}"
    
    def fetch_permissions():
        # Complex permission calculation involving multiple queries
        # to user groups, roles, and permission tables
        ...
        return permissions
    
    # Cache permissions for 1 hour
    return get_or_set_cache(cache_key, fetch_permissions, timeout=60*60)


def invalidate_user_permissions(user_id):
    """Invalidate the cached permissions when they change."""
    cache_key = f"user_permissions:{user_id}"
    return invalidate_cache(cache_key)
```

**Benefits:**
- Reduces authorization overhead for each request
- Improves response times for permission-protected routes
- Centralizes permission logic while maintaining performance

### 4. Caching External API Responses

Calls to external APIs can be slow and may have rate limits. Caching these responses can improve performance and reduce the risk of hitting rate limits.

```python
def fetch_external_api_data(endpoint, params=None):
    """Fetch data from an external API with caching."""
    param_str = "&".join(f"{k}={v}" for k, v in (params or {}).items())
    cache_key = f"external_api:{endpoint}:{param_str}"
    
    def fetch_data():
        # Make the actual API request
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()
    
    # Cache the API response for 30 minutes
    return get_or_set_cache(cache_key, fetch_data, timeout=60*30)
```

**Benefits:**
- Reduces external API calls, avoiding rate limits
- Improves response times for external data
- Provides resilience against external API outages
- Reduces costs for paid APIs

### 5. Caching Rendered Templates

Template rendering can be expensive, especially for complex templates with many context variables. Django provides built-in support for caching rendered templates.

```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # Cache for 15 minutes
def cached_template_view(request):
    """Example view that caches the entire rendered template."""
    # Expensive data gathering and processing
    context = {...}
    return render(request, 'example_template.html', context)
```

For more granular control, you can cache specific template fragments:

```python
def cached_template_fragment(request):
    """Example view that demonstrates caching template fragments."""
    user_id = request.user.id
    
    # Get or compute expensive parts that can be cached
    def get_expensive_fragment():
        # Complex rendering logic
        return rendered_html
    
    # Cache the expensive fragment for 1 hour
    expensive_fragment = get_or_set_cache(
        f"template_fragment:expensive:{user_id}",
        get_expensive_fragment,
        timeout=60*60
    )
    
    # Combine with non-cached, personalized content
    context = {
        'expensive_fragment': expensive_fragment,
        'personalized_content': get_personalized_content(request.user)
    }
    return render(request, 'template_with_fragments.html', context)
```

**Benefits:**
- Reduces rendering time for complex templates
- Allows caching of expensive template fragments while keeping other parts dynamic
- Improves page load times for users

## Cache Invalidation Strategies

Effective cache invalidation is crucial for maintaining data consistency while benefiting from caching performance gains.

### 1. Using Signals to Invalidate Caches

Django signals can automatically invalidate caches when the underlying data changes.

```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=User)
def invalidate_user_cache_on_save(sender, instance, created, **kwargs):
    """Invalidate user-related caches when a user is updated."""
    # Invalidate specific user cache
    invalidate_cache(f"user:{instance.id}")
    
    # If this is a new user, also invalidate the user list cache
    if created:
        invalidate_cache('user_list')

@receiver(post_delete, sender=User)
def invalidate_user_cache_on_delete(sender, instance, **kwargs):
    """Invalidate user-related caches when a user is deleted."""
    invalidate_cache(f"user:{instance.id}")
    invalidate_cache('user_list')
```

**Benefits:**
- Automatic cache invalidation without manual intervention
- Ensures data consistency across the application
- Centralizes invalidation logic in signal handlers

### 2. Implementing Versioned Cache Keys

Versioned cache keys provide a sophisticated way to invalidate multiple related caches at once.

```python
class VersionedCache:
    @staticmethod
    def get_version(resource_type):
        """Get the current version for a resource type."""
        version_key = f"cache_version:{resource_type}"
        version = cache.get(version_key)
        
        if version is None:
            # Initialize with version 1 if not set
            version = '1'
            cache.set(version_key, version, timeout=None)  # No expiration
            
        return version
    
    @staticmethod
    def increment_version(resource_type):
        """Increment the version, invalidating all related caches."""
        version_key = f"cache_version:{resource_type}"
        current_version = cache.get(version_key, '0')
        
        new_version = str(int(current_version) + 1)
        cache.set(version_key, new_version, timeout=None)  # No expiration
        
        return new_version
    
    @staticmethod
    def get_key(resource_type, key_suffix):
        """Generate a versioned cache key."""
        version = VersionedCache.get_version(resource_type)
        return f"{resource_type}:v{version}:{key_suffix}"


# Example usage
def get_cached_products(category=None):
    """Get products with versioned caching."""
    key_suffix = f"products:{category or 'all'}"
    cache_key = VersionedCache.get_key('product', key_suffix)
    
    # Check if the data is in the cache
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    # If not in cache, fetch and cache the data
    products = fetch_products(category)
    cache.set(cache_key, products, timeout=60*60)
    return products


def invalidate_product_cache():
    """Invalidate all product caches by incrementing the version."""
    return VersionedCache.increment_version('product')
```

**Benefits:**
- Instantly invalidates all related caches with a single operation
- No need to track and invalidate individual cache keys
- Efficient for invalidating large groups of related caches
- Prevents stale data issues when multiple caches depend on the same data

## Configuration

The Redis cache is configured in `settings.py`:

```python
# Redis Cache Configuration
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://redis:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_CLASS": "redis.BlockingConnectionPool",
            "CONNECTION_POOL_CLASS_KWARGS": {
                "max_connections": 50,
                "timeout": 20,
            },
            "MAX_CONNECTIONS": 1000,
            "IGNORE_EXCEPTIONS": True,
        },
    }
}

# Default cache time to live is 15 minutes
CACHE_TTL = 60 * 15
```

## Best Practices

1. **Choose Appropriate Timeouts**: Set cache timeouts based on how frequently the data changes and how critical it is to have the latest data.

2. **Cache Invalidation**: Implement proper cache invalidation when data is updated to ensure users see the latest information.

3. **Handle Exceptions**: The cache is configured with `IGNORE_EXCEPTIONS=True`, which means cache failures won't break your application, but you should still handle potential cache misses gracefully.

4. **Monitor Cache Usage**: Keep an eye on Redis memory usage and performance to ensure optimal operation.

5. **Test Cache Behavior**: Write tests that verify both cache hits and cache misses to ensure your caching logic works correctly.

## Testing

The Redis caching implementation includes comprehensive tests that verify all caching functionality. You can run these tests with:

```bash
python manage.py test tests.test_redis_cache_unit

```

## Conclusion

Implementing Redis caching in your Django application can significantly improve performance by reducing database load, speeding up API responses, and optimizing resource-intensive operations.

By using the techniques and examples provided in this documentation, you can effectively implement caching for various scenarios and ensure proper cache invalidation to maintain data consistency.

Remember to carefully consider what data to cache, for how long, and how to invalidate it when the underlying data changes. With proper caching strategies, you can achieve substantial performance improvements while maintaining data integrity.
