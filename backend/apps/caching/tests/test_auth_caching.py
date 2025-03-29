import hashlib
import json
import time
from unittest.mock import patch, MagicMock

from django.test import TestCase, RequestFactory, override_settings
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.views.auth_view import get_current_user
from apps.users.models import User


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
        self.user = User.objects.create_user(
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
        # First call should cache the result
        with patch('apps.users.views.auth_view.cache.get') as mock_cache_get, \
             patch('apps.users.views.auth_view.cache.set') as mock_cache_set:
            mock_cache_get.return_value = None
            
            # Make actual API call to the view
            response1 = self.client.get(reverse('get_current_user'))
            
            # Verify cache.get was called
            mock_cache_get.assert_called_once()
            
            # Verify cache.set was called with the correct data
            mock_cache_set.assert_called_once()
            
            # Get the cache key that was used
            cache_key = mock_cache_get.call_args[0][0]
            
            # Verify the cache key format
            token_hash = hashlib.md5(self.token.encode()).hexdigest()
            expected_key = f"user_info:{token_hash}"
            self.assertEqual(cache_key, expected_key)
            
            # Verify response is successful
            self.assertEqual(response1.status_code, 200)
    
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
        
        # Call should use cached data
        with patch('apps.users.views.auth_view.auth_service.get_user_by_token') as mock_get_user:
            # Make actual API call to the view
            response = self.client.get(reverse('get_current_user'))
            
            # Verify auth_service was not called (cache hit)
            mock_get_user.assert_not_called()
            
            # Verify response contains cached data
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["id"], self.user.id)
            self.assertEqual(response.data["username"], self.user.username)
    
    def test_get_current_user_invalid_token(self):
        """Test that get_current_user handles invalid tokens correctly."""
        # Use an invalid token
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid_token")
        
        # Make actual API call to the view
        response = self.client.get(reverse('get_current_user'))
        
        # Verify response is unauthorized
        self.assertEqual(response.status_code, 401)
    
    def test_get_current_user_performance(self):
        """Test performance improvement with caching."""
        # First request (cache miss) should be slower
        with patch('apps.users.views.auth_view.auth_service.get_user_by_token', side_effect=lambda token: {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email
        }):
            start_time = time.time()
            response1 = self.client.get(reverse('get_current_user'))
            first_request_time = time.time() - start_time
        
        # Second request (cache hit) should be faster
        start_time = time.time()
        response2 = self.client.get(reverse('get_current_user'))
        second_request_time = time.time() - start_time
        
        # Verify second request was faster
        self.assertLess(second_request_time, first_request_time)
        
        # Verify both responses are successful
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
