from functools import wraps
from typing import Any, Callable, Optional, TypeVar, cast
import hashlib
import json
import logging
from django.core.cache import cache

# Type variable for generic return types
T = TypeVar('T')

logger = logging.getLogger(__name__)


def get_cached_result(key: str, default: Any = None) -> Any:
    """
    Get a result from the cache.
    
    Args:
        key: The cache key to retrieve
        default: Value to return if key is not found (default: None)
        
    Returns:
        The cached value or the default value if not found
    """
    try:
        return cache.get(key, default)
    except Exception as e:
        logger.warning(f"Error retrieving from cache: {str(e)}")
        return default


def invalidate_cache(key: str) -> bool:
    """
    Invalidate a specific cache key.
    
    Args:
        key: The cache key to invalidate
        
    Returns:
        True if the key was found and deleted, False otherwise
    """
    try:
        return bool(cache.delete(key))
    except Exception as e:
        logger.warning(f"Error invalidating cache: {str(e)}")
        return False


def get_or_set_cache(key: str, func: Callable[[], T], timeout: Optional[int] = None) -> T:
    """
    Get a value from the cache, or compute and store it if not found.
    
    Args:
        key: The cache key to retrieve or store
        func: Function to call if the key is not in the cache
        timeout: Optional cache timeout in seconds
        
    Returns:
        The cached or computed value
    """
    result = cache.get(key)
    if result is None:
        try:
            result = func()
            cache.set(key, result, timeout)
        except Exception as e:
            logger.error(f"Error computing or caching result: {str(e)}")
            raise
    return cast(T, result)


def cache_result(timeout: Optional[int] = None, key_prefix: str = ""):
    """
    Decorator that caches the result of a function based on its arguments.
    
    Args:
        timeout: Optional cache timeout in seconds
        key_prefix: Optional prefix for the cache key
        
    Returns:
        Decorated function that uses caching
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate a cache key based on the function name and arguments
            key_parts = [key_prefix] if key_prefix else []
            key_parts.append(func.__module__)
            key_parts.append(func.__name__)
            
            # Add args and kwargs to the key
            if args:
                key_parts.append(hashlib.md5(str(args).encode()).hexdigest())
            
            if kwargs:
                # Sort kwargs by key for consistent cache keys
                sorted_kwargs = json.dumps(kwargs, sort_keys=True)
                key_parts.append(hashlib.md5(sorted_kwargs.encode()).hexdigest())
            
            cache_key = ":".join(key_parts)
            
            # Try to get from cache first
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result
            
            # If not in cache, call the function and cache the result
            logger.debug(f"Cache miss for {cache_key}, computing result")
            result = func(*args, **kwargs)
            try:
                cache.set(cache_key, result, timeout)
                logger.debug(f"Cached result for {cache_key} with timeout {timeout}")
            except Exception as e:
                logger.warning(f"Failed to cache result for {cache_key}: {str(e)}")
            
            return result
        return wrapper
    return decorator
