from django.test import SimpleTestCase
from django.core.cache import cache
from unittest import mock
import time

# Import the Redis functions we want to test
from apps.caching.utils.redis_cache import (
    get_cached_result,
    invalidate_cache,
    get_or_set_cache,
    cache_result
)


class RedisCacheUnitTest(SimpleTestCase):
    """Unit tests for Redis caching functionality without database dependencies"""

    def setUp(self):
        # Clear cache before each test
        cache.clear()

    def tearDown(self):
        # Clear cache after each test
        cache.clear()

    def test_simple_cache_operations(self):
        """Test basic cache operations using Django's cache framework"""
        # Test simple set/get operations
        cache.set('test_key', 'test_value', 60)
        value = cache.get('test_key')
        self.assertEqual(value, 'test_value')
        
        # Test deleting a key
        cache.delete('test_key')
        value = cache.get('test_key')
        self.assertIsNone(value)

    def test_get_or_set_cache(self):
        """Test the get_or_set_cache utility function"""
        # Define a mock function that counts calls
        mock_func = mock.MagicMock(return_value="test_value")
        
        # First call should call the function and cache the result
        result1 = get_or_set_cache("test_key", mock_func, 60)
        self.assertEqual(result1, "test_value")
        mock_func.assert_called_once()

        # Second call should return cached value without calling the function again
        mock_func.reset_mock()
        result2 = get_or_set_cache("test_key", mock_func, 60)
        self.assertEqual(result2, "test_value")
        mock_func.assert_not_called()
    
    def test_cache_result_decorator(self):
        """Test the cache_result decorator"""
        counter = [0]  # Use a list to allow modification in nested function

        @cache_result(timeout=60)
        def example_function(param):
            counter[0] += 1
            return f"Result: {param} - {counter[0]}"

        # First call should execute the function
        result1 = example_function("test")
        self.assertEqual(result1, "Result: test - 1")
        
        # Second call with same param should use cached result
        result2 = example_function("test")
        self.assertEqual(result2, "Result: test - 1")  # Counter should not increment
        
        # Call with different param should execute the function again
        result3 = example_function("different")
        self.assertEqual(result3, "Result: different - 2")

    def test_invalidate_cache(self):
        """Test invalidating specific cache keys"""
        # Set up some cache values
        cache.set("key1", "value1", 60)
        cache.set("key2", "value2", 60)
        
        # Verify values are cached
        self.assertEqual(cache.get("key1"), "value1")
        self.assertEqual(cache.get("key2"), "value2")
        
        # Invalidate specific key
        invalidate_cache("key1")
        
        # Verify only the specified key was invalidated
        self.assertIsNone(cache.get("key1"))
        self.assertEqual(cache.get("key2"), "value2")

    def test_get_cached_result(self):
        """Test retrieving cached results directly"""
        # Set a cache value
        cache.set("direct_key", "direct_value", 60)
        
        # Retrieve it using our function
        result = get_cached_result("direct_key")
        self.assertEqual(result, "direct_value")
        
        # Test with a key that doesn't exist
        result_none = get_cached_result("nonexistent_key")
        self.assertIsNone(result_none)
        
        # Test with a default value for nonexistent key
        result_default = get_cached_result("nonexistent_key", default="default_value")
        self.assertEqual(result_default, "default_value")
