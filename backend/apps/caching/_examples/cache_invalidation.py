from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
import hashlib
import time
import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.caching.utils.redis_cache import invalidate_cache

logger = logging.getLogger(__name__)

# For demonstration purposes - replace with your actual models
try:
    from django.contrib.auth import get_user_model
    User = get_user_model()
except ImportError:
    User = None


# ---------------------------------------------------------------
# Signal-based cache invalidation
# ---------------------------------------------------------------

# Define cache key patterns for different model types
CACHE_KEYS = {
    'user': [
        'user_list',  # Cache key for list of all users
        'user_count',  # Cache key for count of users
        'user_permissions:*',  # Pattern for user permission cache keys
    ],
    'product': [
        'product_list',
        'product_detail:*',
        'featured_products',
    ],
    # Add more models and their cache keys as needed
}


def invalidate_model_caches(model_type, instance_id=None):
    """
    Invalidate all caches related to a specific model type and optionally a specific instance.
    
    This function demonstrates how to invalidate multiple related cache keys
    when a model instance is created, updated, or deleted.
    """
    if model_type not in CACHE_KEYS:
        return
    
    logger.info(f"Invalidating caches for {model_type} (id={instance_id})")
    
    # Get all cache key patterns for this model type
    cache_key_patterns = CACHE_KEYS[model_type]
    
    for pattern in cache_key_patterns:
        if '*' in pattern and instance_id is not None:
            # For wildcard patterns, invalidate the specific instance
            specific_key = pattern.replace('*', str(instance_id))
            invalidate_cache(specific_key)
            logger.debug(f"Invalidated cache key: {specific_key}")
        else:
            # For non-wildcard patterns, invalidate the entire key
            invalidate_cache(pattern)
            logger.debug(f"Invalidated cache key: {pattern}")


# Signal handlers for User model (if available)
if User:
    @receiver(post_save, sender=User)
    def invalidate_user_cache_on_save(sender, instance, created, **kwargs):
        """
        Signal handler to invalidate user-related caches when a user is created or updated.
        
        This demonstrates how to use Django signals to automatically invalidate
        cache entries when the underlying data changes.
        """
        invalidate_model_caches('user', instance.id)
        
        # If user permissions might have changed, invalidate permission cache
        invalidate_cache(f"user_permissions:{instance.id}")
        
        # If this is a new user, also invalidate the user count cache
        if created:
            invalidate_cache('user_count')
    
    @receiver(post_delete, sender=User)
    def invalidate_user_cache_on_delete(sender, instance, **kwargs):
        """
        Signal handler to invalidate user-related caches when a user is deleted.
        """
        invalidate_model_caches('user', instance.id)
        invalidate_cache('user_count')


# ---------------------------------------------------------------
# Versioned cache keys for sophisticated invalidation
# ---------------------------------------------------------------

class VersionedCache:
    """
    A utility class for managing versioned cache keys.
    
    This allows for instant invalidation of all caches related to a specific
    resource type by incrementing the version number.
    """
    
    @staticmethod
    def get_version(resource_type):
        """
        Get the current version for a resource type.
        
        Args:
            resource_type: The type of resource (e.g., 'product', 'user')
            
        Returns:
            The current version number as a string
        """
        version_key = f"cache_version:{resource_type}"
        version = cache.get(version_key)
        
        if version is None:
            # Initialize with version 1 if not set
            version = '1'
            cache.set(version_key, version, timeout=None)  # No expiration
            
        return version
    
    @staticmethod
    def increment_version(resource_type):
        """
        Increment the version for a resource type, effectively invalidating all caches.
        
        Args:
            resource_type: The type of resource (e.g., 'product', 'user')
            
        Returns:
            The new version number as a string
        """
        version_key = f"cache_version:{resource_type}"
        current_version = cache.get(version_key, '0')
        
        try:
            new_version = str(int(current_version) + 1)
        except ValueError:
            new_version = '1'
            
        cache.set(version_key, new_version, timeout=None)  # No expiration
        logger.info(f"Incremented cache version for {resource_type}: {current_version} -> {new_version}")
        
        return new_version
    
    @staticmethod
    def get_key(resource_type, key_suffix):
        """
        Generate a versioned cache key for a specific resource.
        
        Args:
            resource_type: The type of resource (e.g., 'product', 'user')
            key_suffix: The specific key identifier (e.g., 'list', 'detail:123')
            
        Returns:
            A versioned cache key string
        """
        version = VersionedCache.get_version(resource_type)
        return f"{resource_type}:v{version}:{key_suffix}"


# Example functions using versioned cache
def get_cached_products(category=None):
    """
    Get a list of products with versioned caching.
    
    This demonstrates how to use versioned cache keys to fetch data.
    """
    # Create a cache key with the current version
    key_suffix = f"products:{category or 'all'}"
    cache_key = VersionedCache.get_key('product', key_suffix)
    
    # Check if the data is in the cache
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        logger.debug(f"Cache hit for {cache_key}")
        return cached_data
    
    # If not in cache, fetch the data (simulated here)
    logger.info(f"Cache miss for {cache_key}, fetching products")
    time.sleep(1)  # Simulate database query
    
    # Mock product data
    products = [
        {"id": 1, "name": "Product 1", "price": 19.99, "category": "electronics"},
        {"id": 2, "name": "Product 2", "price": 29.99, "category": "clothing"},
        {"id": 3, "name": "Product 3", "price": 9.99, "category": "electronics"},
    ]
    
    # Filter by category if specified
    if category:
        products = [p for p in products if p["category"] == category]
    
    # Cache the result for 1 hour
    cache.set(cache_key, products, timeout=60*60)
    
    return products


def invalidate_product_cache():
    """
    Invalidate all product-related caches by incrementing the version.
    
    This demonstrates how to use versioned cache keys for invalidation.
    """
    # Simply increment the version to invalidate all product caches
    new_version = VersionedCache.increment_version('product')
    return new_version


# API views for demonstration
@api_view(['GET'])
def cached_products_view(request):
    """
    View that returns cached products using versioned cache keys.
    """
    category = request.query_params.get('category')
    products = get_cached_products(category)
    
    return Response({
        "products": products,
        "count": len(products),
        "category": category or "all",
        "timestamp": time.time()
    })


@api_view(['POST'])
def invalidate_product_cache_view(request):
    """
    View that invalidates all product caches by incrementing the version.
    """
    new_version = invalidate_product_cache()
    
    return Response({
        "message": "All product caches have been invalidated",
        "new_version": new_version,
        "timestamp": time.time()
    })
