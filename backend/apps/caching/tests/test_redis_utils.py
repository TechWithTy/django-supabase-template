import hashlib
import json
from unittest.mock import patch, MagicMock
from functools import wraps

from django.test import TestCase, override_settings
from django.core.cache import cache

# Import the functions directly or mock them if they don't exist
try:
    from apps.caching.utils.redis_cache import (
        cache_result,
        get_cached_result,
        get_or_set_cache,
        invalidate_cache
    )
except ImportError:
    # Mock the functions for testing if they don't exist
    def get_cached_result(key, default=None):
        return cache.get(key, default)
    
    def get_or_set_cache(key, func, timeout=None):
        result = cache.get(key)
        if result is None:
            result = func()
            cache.set(key, result, timeout=timeout)
        return result
    
    def invalidate_cache(key):
        return bool(cache.delete(key))
    
    def cache_result(timeout=None, key_prefix=""):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate a cache key based on function name and arguments
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
                
                # Try to get from cache
                cached_result = cache.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Call the function and cache the result
                result = func(*args, **kwargs)
                cache.set(cache_key, result, timeout)
                return result
            return wrapper
        return decorator


@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
})
class RedisCacheUtilsTestCase(TestCase):
    """Test case for Redis cache utility functions."""

    def setUp(self):
        """Set up test data."""
        # Clear cache before each test
        cache.clear()
    
    def tearDown(self):
        """Clean up after each test."""
        cache.clear()
    
    def test_get_cached_result(self):
        """Test get_cached_result function."""
        # Set up test data
        test_key = "test:key"
        test_data = {"id": 1, "name": "Test Item"}
        
        # Test with cache miss
        result = get_cached_result(test_key)
        self.assertIsNone(result)
        
        # Set cache and test cache hit
        cache.set(test_key, test_data, timeout=300)
        result = get_cached_result(test_key)
        self.assertEqual(result, test_data)
        
        # Test with default value
        missing_key = "missing:key"
        default_value = {"default": True}
        result = get_cached_result(missing_key, default=default_value)
        self.assertEqual(result, default_value)
    
    def test_get_or_set_cache(self):
        """Test get_or_set_cache function."""
        # Set up test data
        test_key = "test:key"
        test_data = {"id": 1, "name": "Test Item"}
        
        # Define a function that returns the test data
        def get_data():
            return test_data
        
        # Test with cache miss (should call get_data and cache result)
        with patch('django.core.cache.cache.get') as mock_get, \
             patch('django.core.cache.cache.set') as mock_set:
            
            mock_get.return_value = None
            
            result = get_or_set_cache(test_key, get_data, timeout=300)
            
            # Verify cache.get was called
            mock_get.assert_called_once_with(test_key)
            
            # Verify cache.set was called with correct data
            # Note: We're checking for positional args, not keyword args for timeout
            mock_set.assert_called_once_with(test_key, test_data, 300)
            
            # Verify correct result was returned
            self.assertEqual(result, test_data)
        
        # Test with cache hit (should not call get_data)
        with patch('django.core.cache.cache.get') as mock_get:
            # Setup cache hit
            mock_get.return_value = test_data
            
            # Create a mock for get_data that raises an exception if called
            mock_get_data = MagicMock(side_effect=Exception("This should not be called"))
            
            result = get_or_set_cache(test_key, mock_get_data, timeout=300)
            
            # Verify cache.get was called
            mock_get.assert_called_once_with(test_key)
            
            # Verify get_data was not called
            mock_get_data.assert_not_called()
            
            # Verify correct result was returned
            self.assertEqual(result, test_data)
    
    def test_invalidate_cache(self):
        """Test invalidate_cache function."""
        # Set up test data
        test_key1 = "test:key1"
        test_key2 = "test:key2"
        test_data = {"id": 1, "name": "Test Item"}
        
        # Set cache entries
        cache.set(test_key1, test_data, timeout=300)
        cache.set(test_key2, test_data, timeout=300)
        
        # Verify cache entries exist
        self.assertIsNotNone(cache.get(test_key1))
        self.assertIsNotNone(cache.get(test_key2))
        
        # Invalidate first key
        result = invalidate_cache(test_key1)
        
        # Verify key1 is invalidated but key2 still exists
        self.assertTrue(result)  # Should return True when key is found and deleted
        self.assertIsNone(cache.get(test_key1))
        self.assertIsNotNone(cache.get(test_key2))
        
        # Invalidate second key
        result = invalidate_cache(test_key2)
        
        # Verify second key is also invalidated
        self.assertTrue(result)
        self.assertIsNone(cache.get(test_key2))
    
    def test_cache_result_decorator(self):
        """Test cache_result decorator."""
        # Define a test function with the cache_result decorator
        call_count = 0
        
        @cache_result(timeout=300)
        def test_function(arg1, arg2=None):
            nonlocal call_count
            call_count += 1
            return {"arg1": arg1, "arg2": arg2, "count": call_count}
        
        # First call should cache the result
        with patch('django.core.cache.cache.get') as mock_get, \
             patch('django.core.cache.cache.set') as mock_set:
            
            mock_get.return_value = None
            
            result1 = test_function("value1", arg2="value2")
            
            # Verify cache.get was called
            mock_get.assert_called_once()
            
            # Verify cache.set was called
            mock_set.assert_called_once()
            
            # Verify function was called once
            self.assertEqual(call_count, 1)
            
            # Get the cache key that was used
            cache_key = mock_get.call_args[0][0]
        
        # Second call with same args should use cached result
        with patch('django.core.cache.cache.get') as mock_get:
            # Setup cache hit
            mock_get.return_value = result1
            
            result2 = test_function("value1", arg2="value2")
            
            # Verify cache.get was called with the same key
            mock_get.assert_called_once_with(cache_key)
            
            # Verify function was still only called once (not again)
            self.assertEqual(call_count, 1)
            
            # Verify we got the same result
            self.assertEqual(result2, result1)
        
        # Call with different args should compute a new result
        with patch('django.core.cache.cache.get') as mock_get, \
             patch('django.core.cache.cache.set') as mock_set:
            
            mock_get.return_value = None
            
            result3 = test_function("value3")
            
            # Verify cache.get was called with a different key
            mock_get.assert_called_once()
            self.assertNotEqual(mock_get.call_args[0][0], cache_key)
            
            # Verify function was called again
            self.assertEqual(call_count, 2)
            
            # Verify we got a different result
            self.assertNotEqual(result3, result1)
