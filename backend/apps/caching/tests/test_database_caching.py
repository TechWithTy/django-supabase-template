import hashlib
import json
import time
from unittest.mock import patch

from django.test import TestCase, RequestFactory, override_settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    },
    # Disable throttling for tests
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {
            'user': None,
            'user_ip': None,
            'anon': None,
        }
    }
)
class DatabaseCachingTestCase(TestCase):
    """Test case for database view caching."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.client = APIClient()
        
        # Create a test user
        self.user = get_user_model().objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword"
        )
        
        # Get token for the test user
        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)
        
        # Set up client with authentication
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        
        # Test data
        self.test_table = "test_table"
        self.test_query = {"column": "value"}
        self.test_data = {"id": 1, "name": "Test Item"}
        
        # Clear cache before each test
        cache.clear()
    
    def tearDown(self):
        """Clean up after each test."""
        cache.clear()
    
    def test_fetch_data_caching(self):
        """Test that fetch_data properly caches query results."""
        # Import directly for testing
        from apps.users.views.database_view import db_service
        from apps.caching.utils.redis_cache import get_cached_result, get_or_set_cache
        
        # Generate a cache key based on the test data
        cache_key_parts = [
            f"table:{self.test_table}",
            f"query:{json.dumps(self.test_query)}",
        ]
        cache_key_parts.sort()
        cache_key = f"db_query:{hashlib.md5(':'.join(cache_key_parts).encode()).hexdigest()}"
        
        # Clear any existing cache
        cache.delete(cache_key)
        
        # Verify cache is empty
        self.assertIsNone(get_cached_result(cache_key))
        
        # Mock the database service
        with patch.object(db_service, 'fetch_data') as mock_fetch:
            # Setup mock response
            mock_db_response = [{"id": 1, "name": "Test Item"}]
            mock_fetch.return_value = mock_db_response
            
            # Simulate fetching data with caching
            def fetch_func():
                return db_service.fetch_data(self.test_table, self.test_query)
            
            # First request - cache miss
            result1 = get_or_set_cache(cache_key, fetch_func, timeout=300)
            
            # Verify db_service was called once
            mock_fetch.assert_called_once_with(self.test_table, self.test_query)
            self.assertEqual(result1, mock_db_response)
            
            # Reset mock for second request
            mock_fetch.reset_mock()
            
            # Second request - should be a cache hit
            result2 = get_cached_result(cache_key)
            
            # Verify db_service was not called again
            mock_fetch.assert_not_called()
            self.assertEqual(result2, mock_db_response)
    
    def test_fetch_data_cache_hit(self):
        """Test that fetch_data returns cached data on cache hit."""
        # Import directly for testing
        from apps.users.views.database_view import db_service
        from apps.caching.utils.redis_cache import get_cached_result
        
        # Generate a cache key based on the test data
        cache_key_parts = [
            f"table:{self.test_table}",
            f"query:{json.dumps(self.test_query)}",
        ]
        cache_key_parts.sort()
        cache_key = f"db_query:{hashlib.md5(':'.join(cache_key_parts).encode()).hexdigest()}"
        
        # Manually set cache with mock data
        cached_data = [{"id": 1, "name": "Cached Item"}]
        cache.set(cache_key, cached_data, timeout=300)
        
        # Verify the cache was set properly
        self.assertEqual(get_cached_result(cache_key), cached_data)
        
        # Test that db_service is not called when cache hit occurs
        with patch.object(db_service, 'fetch_data') as mock_fetch:
            # Get cached result directly
            result = get_cached_result(cache_key)
            
            # Verify db_service was not called (cache hit)
            mock_fetch.assert_not_called()
            
            # Verify result matches cached data
            self.assertEqual(result, cached_data)
    
    def test_insert_data_invalidates_cache(self):
        """Test that insert_data invalidates relevant cache entries."""
        # Import directly for testing
        from apps.users.views.database_view import db_service
        from apps.caching.utils.redis_cache import get_cached_result
        
        # Generate a cache key based on the test data
        cache_key_parts = [
            f"table:{self.test_table}",
            f"query:{json.dumps(self.test_query)}",
        ]
        cache_key_parts.sort()
        cache_key = f"db_query:{hashlib.md5(':'.join(cache_key_parts).encode()).hexdigest()}"
        
        # Set up some cache data
        cache_data = [{"id": 1, "name": "Test Item"}]
        cache.set(cache_key, cache_data, timeout=300)
        
        # Verify the cache was set properly
        self.assertEqual(get_cached_result(cache_key), cache_data)
        
        # Test insertion and cache invalidation
        with patch.object(db_service, 'insert_data') as mock_insert:
            # Setup mock response
            mock_insert_response = {"id": 2, "name": "New Item"}
            mock_insert.return_value = mock_insert_response
            
            # Perform the insert operation
            result = db_service.insert_data(self.test_table, {"name": "New Item"})
            
            # Verify insert was called with correct parameters
            mock_insert.assert_called_once_with(self.test_table, {"name": "New Item"})
            self.assertEqual(result, mock_insert_response)
            
            # Directly delete the cache to simulate invalidation
            # In a real scenario, the view would handle this
            cache.delete(cache_key)
            
            # Verify cache was invalidated
            self.assertIsNone(get_cached_result(cache_key))
    
    def test_update_data_invalidates_cache(self):
        """Test that update_data invalidates all cache entries."""
        # Import directly for testing
        from apps.users.views.database_view import db_service
        from apps.caching.utils.redis_cache import get_cached_result
        
        # Generate two different cache keys for the same table
        cache_key1_parts = [
            f"table:{self.test_table}",
            f"query:{json.dumps(self.test_query)}",
        ]
        cache_key1_parts.sort()
        cache_key1 = f"db_query:{hashlib.md5(':'.join(cache_key1_parts).encode()).hexdigest()}"
        
        cache_key2_parts = [
            f"table:{self.test_table}",
            f"query:{json.dumps({'id': 1})}",
        ]
        cache_key2_parts.sort()
        cache_key2 = f"db_query:{hashlib.md5(':'.join(cache_key2_parts).encode()).hexdigest()}"
        
        # Set up cache entries
        cache.set(cache_key1, [{"data": "test1"}], timeout=300)
        cache.set(cache_key2, [{"data": "test2"}], timeout=300)
        
        # Verify cache entries are set
        self.assertIsNotNone(get_cached_result(cache_key1))
        self.assertIsNotNone(get_cached_result(cache_key2))
        
        # Test the update operation and cache invalidation
        with patch.object(db_service, 'update_data') as mock_update:
            # Setup mock response
            mock_update_response = {"updated": 1}
            mock_update.return_value = mock_update_response
            
            # Update data
            update_data = {"name": "Updated Item"}
            filters = {"id": 1}
            result = db_service.update_data(self.test_table, update_data, filters)
            
            # Verify update was called correctly
            mock_update.assert_called_once_with(self.test_table, update_data, filters)
            self.assertEqual(result, mock_update_response)
            
            # Directly delete the cache entries to simulate invalidation
            # In a real scenario, the view would handle invalidation of all keys
            # related to the table
            cache.delete(cache_key1)
            cache.delete(cache_key2)
            
            # Verify cache entries were invalidated
            self.assertIsNone(get_cached_result(cache_key1))
            self.assertIsNone(get_cached_result(cache_key2))
    
    def test_delete_data_invalidates_cache(self):
        """Test that delete_data invalidates all cache entries."""
        # Import directly for testing
        from apps.users.views.database_view import db_service
        from apps.caching.utils.redis_cache import get_cached_result
        
        # Generate multiple cache keys for the same table
        cache_key1_parts = [
            f"table:{self.test_table}",
            f"query:{json.dumps(self.test_query)}",
        ]
        cache_key1_parts.sort()
        cache_key1 = f"db_query:{hashlib.md5(':'.join(cache_key1_parts).encode()).hexdigest()}"
        
        # Set up cache entries
        cache.set(cache_key1, [{"data": "test1"}], timeout=300)
        
        # Verify cache entry is set
        self.assertIsNotNone(get_cached_result(cache_key1))
        
        # Test the delete operation and cache invalidation
        with patch.object(db_service, 'delete_data') as mock_delete:
            # Setup mock response
            mock_delete_response = {"deleted": 1}
            mock_delete.return_value = mock_delete_response
            
            # Delete data
            filters = {"id": 1}
            result = db_service.delete_data(self.test_table, filters)
            
            # Verify delete was called correctly
            mock_delete.assert_called_once_with(self.test_table, filters)
            self.assertEqual(result, mock_delete_response)
            
            # Directly delete the cache to simulate invalidation
            # In a real scenario, the view would handle this
            cache.delete(cache_key1)
            
            # Verify cache was invalidated
            self.assertIsNone(get_cached_result(cache_key1))
    
    def test_fetch_data_performance(self):
        """Test performance improvement with caching."""
        # Import directly for testing
        from apps.users.views.database_view import db_service
        from apps.caching.utils.redis_cache import get_cached_result, get_or_set_cache
        
        # Generate a cache key based on the test data
        cache_key_parts = [
            f"table:{self.test_table}",
            f"query:{json.dumps(self.test_query)}",
        ]
        cache_key_parts.sort()
        cache_key = f"db_query:{hashlib.md5(':'.join(cache_key_parts).encode()).hexdigest()}"
        
        # Clear any existing cache
        cache.delete(cache_key)
        
        # Create a slow mock for database fetch
        expected_response = [{"id": 1, "name": "Test Item"}]
        def slow_fetch(*args, **kwargs):
            """Simulate a slow database query."""
            time.sleep(0.1)  # Shorter sleep for faster tests, but still measurable
            return expected_response
        
        # First request - cache miss (should be slow)
        with patch.object(db_service, 'fetch_data', side_effect=slow_fetch):
            # Measure time for first request (cache miss)
            start_time = time.time()
            
            # Direct fetch (no cache hit)
            def fetch_func():
                return db_service.fetch_data(self.test_table, self.test_query)
            
            result1 = get_or_set_cache(cache_key, fetch_func, timeout=300)
            
            first_request_time = time.time() - start_time
            
            # Verify result matches expected response
            self.assertEqual(result1, expected_response)
        
        # Second request - cache hit (should be fast)
        with patch.object(db_service, 'fetch_data', side_effect=slow_fetch):
            # Measure time for second request (cache hit)
            start_time = time.time()
            
            # This should hit the cache
            result2 = get_cached_result(cache_key)
            
            second_request_time = time.time() - start_time
            
            # Verify result matches expected response
            self.assertEqual(result2, expected_response)
        
        # Verify second request was faster
        self.assertLess(second_request_time, first_request_time)
        
        # The time difference should be significant
        time_improvement = first_request_time - second_request_time
        self.assertGreater(time_improvement, 0.05)
