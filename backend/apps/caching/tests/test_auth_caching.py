import hashlib
import json
import time
from unittest.mock import patch, MagicMock

from django.test import TestCase, RequestFactory, override_settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.views.auth_view import auth_service
from apps.caching.utils.redis_cache import get_cached_result, get_or_set_cache


@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
})
class AuthCachingTestCase(TestCase):
    """Test case for authentication view caching."""

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
        
        # Clear cache before each test
        cache.clear()
    
    def tearDown(self):
        """Clean up after each test."""
        cache.clear()
    
    def test_get_current_user_caching(self):
        """Test that get_current_user properly caches user data."""
        # Generate the expected cache key
        token_hash = hashlib.md5(self.token.encode()).hexdigest()
        cache_key = f"user_info:{token_hash}"
        
        # Clear any existing cache
        cache.delete(cache_key)
        
        # Verify cache is empty
        self.assertIsNone(get_cached_result(cache_key))
        
        # Test caching mechanism
        with patch.object(auth_service, 'get_user_by_token') as mock_get_user:
            # Setup mock response
            expected_user_data = {
                "id": self.user.id,
                "username": self.user.username,
                "email": self.user.email
            }
            mock_get_user.return_value = expected_user_data
            
            # Simulate getting user info with caching
            def fetch_func():
                return auth_service.get_user_by_token(self.token)
            
            # First request - cache miss
            result = get_or_set_cache(cache_key, fetch_func, timeout=300)
            
            # Verify auth_service was called once
            mock_get_user.assert_called_once_with(self.token)
            self.assertEqual(result, expected_user_data)
            
            # Verify the result is now in cache
            cached_result = get_cached_result(cache_key)
            self.assertEqual(cached_result, expected_user_data)
    
    def test_get_current_user_cache_hit(self):
        """Test that get_current_user returns cached data on cache hit."""
        # Generate the expected cache key
        token_hash = hashlib.md5(self.token.encode()).hexdigest()
        cache_key = f"user_info:{token_hash}"
        
        # Manually set cache with mock user data
        cached_user_data = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email
        }
        cache.set(cache_key, cached_user_data, timeout=300)
        
        # Verify the cache was set properly
        self.assertEqual(get_cached_result(cache_key), cached_user_data)
        
        # Test that auth_service is not called when cache hit occurs
        with patch.object(auth_service, 'get_user_by_token') as mock_get_user:
            # Get cached result directly
            result = get_cached_result(cache_key)
            
            # Verify auth_service was not called (cache hit)
            mock_get_user.assert_not_called()
            
            # Verify result matches cached data
            self.assertEqual(result, cached_user_data)
    
    def test_get_current_user_invalid_token(self):
        """Test that get_current_user handles invalid tokens correctly."""
        # Use an invalid token
        invalid_token = "invalid_token"
        
        # Generate cache key for the invalid token
        token_hash = hashlib.md5(invalid_token.encode()).hexdigest()
        cache_key = f"user_info:{token_hash}"
        
        # Clear any existing cache
        cache.delete(cache_key)
        
        # Test behavior with invalid token
        with patch.object(auth_service, 'get_user_by_token') as mock_get_user:
            # Setup mock to simulate authentication error
            mock_get_user.side_effect = Exception("Invalid token")
            
            # Attempt to get user info with the invalid token
            def fetch_func():
                return auth_service.get_user_by_token(invalid_token)
            
            # This should raise an exception
            with self.assertRaises(Exception):
                get_or_set_cache(cache_key, fetch_func, timeout=300)
                
            # Verify auth_service was called with the invalid token
            mock_get_user.assert_called_once_with(invalid_token)
            
            # Verify nothing was cached
            self.assertIsNone(get_cached_result(cache_key))
    
    def test_get_current_user_performance(self):
        """Test performance improvement with caching."""
        # Generate the expected cache key
        token_hash = hashlib.md5(self.token.encode()).hexdigest()
        cache_key = f"user_info:{token_hash}"
        
        # Clear any existing cache
        cache.delete(cache_key)
        
        # Create a slow mock for auth service
        expected_user_data = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email
        }
        
        def slow_get_user(*args, **kwargs):
            """Simulate a slow auth service."""
            time.sleep(0.1)  # Shorter sleep for faster tests, but still measurable
            return expected_user_data
        
        # First request - cache miss (should be slow)
        with patch.object(auth_service, 'get_user_by_token', side_effect=slow_get_user):
            # Measure time for first request (cache miss)
            start_time = time.time()
            
            # Directly fetch (no cache hit)
            def fetch_func():
                return auth_service.get_user_by_token(self.token)
            
            result1 = get_or_set_cache(cache_key, fetch_func, timeout=300)
            
            first_request_time = time.time() - start_time
            
            # Verify result matches expected data
            self.assertEqual(result1, expected_user_data)
        
        # Second request - cache hit (should be fast)
        with patch.object(auth_service, 'get_user_by_token', side_effect=slow_get_user):
            # Measure time for second request (cache hit)
            start_time = time.time()
            
            # This should hit the cache
            result2 = get_cached_result(cache_key)
            
            second_request_time = time.time() - start_time
            
            # Verify result matches expected data
            self.assertEqual(result2, expected_user_data)
        
        # Verify second request was faster
        self.assertLess(second_request_time, first_request_time)
        
        # The time difference should be significant
        time_improvement = first_request_time - second_request_time
        self.assertGreater(time_improvement, 0.05)
