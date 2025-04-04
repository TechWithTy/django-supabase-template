import time
import hashlib
import pytest
from django.test import TestCase, override_settings
from unittest.mock import patch, MagicMock
from django.core.cache import cache
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from rest_framework_simplejwt.tokens import RefreshToken


@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
})
@pytest.mark.django_db
class StorageCachingTestCase(TestCase):
    """Test case for storage caching."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Get the custom user model
        User = get_user_model()
        
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
        
        # Test data
        self.test_bucket = "test-bucket"
        self.test_path = "test/path"
        self.test_file_data = "base64encodeddata"
        
        # Clear cache before each test
        cache.clear()
    
    def tearDown(self):
        """Clean up after each test."""
        cache.clear()
    
    def test_list_objects_caching(self):
        """Test that list_objects properly caches storage listings."""
        # Import the view function directly
        from apps.users.views.client_view import list_objects
        
        # Mock response data (must be serializable)
        mock_response = [{"name": "file1.txt", "size": 1024}]
        
        # First call should cache the result
        with patch('apps.users.views.client_view.supabase.get_storage_service') as mock_get_storage, \
             patch('apps.users.views.client_view.get_cached_result') as mock_cache_get, \
             patch('apps.users.views.client_view.cache.set') as mock_cache_set:
            
            # Setup mock storage service
            mock_storage = MagicMock()
            mock_storage.list_objects.return_value = mock_response
            mock_get_storage.return_value = mock_storage
            
            # Setup cache miss
            mock_cache_get.return_value = None
            
            # Create a factory for the request
            factory = APIRequestFactory()
            
            # Create a request
            request = factory.get(
                f"/api/client/storage/list/?bucket_name={self.test_bucket}&path={self.test_path}"
            )
            
            # Add authentication to the request
            force_authenticate(request, user=self.user)
            
            # Call the view function directly
            response1 = list_objects(request)
            
            # Verify storage service was called
            mock_storage.list_objects.assert_called_once_with(self.test_bucket, self.test_path)
            
            # Verify cache was checked
            mock_cache_get.assert_called_once()
            
            # Verify result was cached
            mock_cache_set.assert_called_once()
            
            # Verify response contains correct data
            self.assertEqual(response1.status_code, 200)
            self.assertEqual(response1.data, mock_response)
    
    def test_list_objects_cache_hit(self):
        """Test that list_objects returns cached data on cache hit."""
        # Import the view function directly
        from apps.users.views.client_view import list_objects
        
        # Generate expected cache key using SHA-256 hash, matching the implementation in the view
        path_hash = hashlib.sha256(self.test_path.encode()).hexdigest()
        cache_key = f"storage:list:{self.test_bucket}:{path_hash}"
        
        # Manually set cache with mock data (must be JSON serializable)
        cached_data = [{"name": "cached_file.txt", "size": 2048}]
        cache.set(cache_key, cached_data, timeout=300)
        
        # Create a factory for the request
        factory = APIRequestFactory()
        
        # Create a request
        request = factory.get(
            f"/api/client/storage/list/?bucket_name={self.test_bucket}&path={self.test_path}"
        )
        
        # Add authentication to the request
        force_authenticate(request, user=self.user)
        
        # Call should use cached data
        with patch('apps.users.views.client_view.supabase.get_storage_service') as mock_get_storage:
            # Setup mock storage (should not be called)
            mock_storage = MagicMock()
            mock_get_storage.return_value = mock_storage
            
            # Call the view function directly
            response = list_objects(request)
            
            # Verify storage service was not called (cache hit)
            mock_storage.list_objects.assert_not_called()
            
            # Verify response contains the cached data
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, cached_data)
    
    def test_upload_file_invalidates_cache(self):
        """Test that upload_file invalidates relevant cache entries."""
        # Set up some cache entries that should be invalidated
        path_hash1 = hashlib.md5(self.test_path.encode()).hexdigest()
        path_hash2 = hashlib.md5("other/path".encode()).hexdigest()
        
        cache_key1 = f"storage:list:{self.test_bucket}:{path_hash1}"
        cache_key2 = f"storage:list:{self.test_bucket}:{path_hash2}"
        cache_key3 = f"storage:list:other-bucket:{path_hash1}"  # Should not be invalidated
        
        cache.set(cache_key1, [{"data": "test1"}], timeout=300)
        cache.set(cache_key2, [{"data": "test2"}], timeout=300)
        cache.set(cache_key3, [{"data": "test3"}], timeout=300)
        
        # Create test file data
        file_content = "base64encodeddata"  # In real scenario, this would be base64 encoded
        
        # Import the view function directly
        from apps.users.views.client_view import upload_file
        
        # Mock the necessary components
        with patch('apps.users.views.client_view.supabase') as mock_supabase, \
             patch.object(cache, 'keys', create=True) as mock_cache_keys, \
             patch.object(cache, 'delete_many') as mock_delete_many:
            
            # Setup mock storage and bucket
            mock_bucket = MagicMock()
            mock_bucket.upload.return_value = {"Key": self.test_path}
            
            mock_storage = MagicMock()
            mock_storage.from_.return_value = mock_bucket
            
            # Setup mock supabase client
            mock_supabase.storage = mock_storage
            
            # Setup mock cache.keys to return our test keys
            mock_cache_keys.side_effect = lambda pattern: [cache_key1, cache_key2] if pattern == f"storage:list:{self.test_bucket}:*" else []
            
            # Create a factory for the request
            factory = APIRequestFactory()
            
            # Create a request with the correct parameters exactly as expected by the view
            request = factory.post(
                "/api/client/storage/upload/",
                {
                    "bucket_name": self.test_bucket,
                    "path": self.test_path,
                    "content": file_content  # Correct parameter name as expected by the view
                },
                format="json"
            )
            
            # Add authentication to the request
            force_authenticate(request, user=self.user)
            
            # Call the view function directly
            response = upload_file(request)
            
            # Verify response contains correct data (201 Created with detailed message)
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.data, {"message": f"File '{self.test_path}' uploaded successfully"})
            
            # Verify storage service was called with correct arguments
            mock_bucket.upload.assert_called_once_with(
                self.test_path, 
                file_content, 
                {"content-type": "application/octet-stream"}
            )
            
            # Verify cache.keys was called with the correct pattern
            mock_cache_keys.assert_called_with(f"storage:list:{self.test_bucket}:*")
            
            # Verify cache.delete_many was called with our test keys
            mock_delete_many.assert_called_with([cache_key1, cache_key2])
        
        # After the test, the actual cache entries should still be there since we mocked delete_many
        self.assertEqual(cache.get(cache_key1), [{"data": "test1"}])
        self.assertEqual(cache.get(cache_key2), [{"data": "test2"}])
        self.assertEqual(cache.get(cache_key3), [{"data": "test3"}])
    
    def test_delete_file_invalidates_cache(self):
        """Test that delete_file invalidates relevant cache entries."""
        # Set up some cache entries that should be invalidated
        path_hash1 = hashlib.md5(self.test_path.encode()).hexdigest()
        path_hash2 = hashlib.md5("other/path".encode()).hexdigest()

        cache_key1 = f"storage:list:{self.test_bucket}:{path_hash1}"
        cache_key2 = f"storage:list:{self.test_bucket}:{path_hash2}"
        cache_key3 = f"storage:list:other-bucket:{path_hash1}"  # Should not be invalidated

        cache.set(cache_key1, [{"data": "test1"}], timeout=300)
        cache.set(cache_key2, [{"data": "test2"}], timeout=300)
        cache.set(cache_key3, [{"data": "test3"}], timeout=300)

        # Verify cache entries were set correctly
        print(f"Initial cache state - key1: {cache.get(cache_key1)}, key2: {cache.get(cache_key2)}, key3: {cache.get(cache_key3)}")

        # Create a test file to delete
        file_path = f"{self.test_path}/file.txt"

        # Import the view function directly
        from apps.users.views.client_view import delete_file

        # Mock the necessary components
        with patch('apps.users.views.client_view.supabase') as mock_supabase, \
             patch.object(cache, 'keys', create=True) as mock_cache_keys, \
             patch.object(cache, 'delete_many') as mock_delete_many:

            # Setup mock storage and bucket
            mock_bucket = MagicMock()
            mock_bucket.remove.return_value = None  # The actual method doesn't return meaningful data
            
            mock_storage = MagicMock()
            mock_storage.from_.return_value = mock_bucket
            
            # Setup mock supabase client
            mock_supabase.storage = mock_storage

            # Setup mock cache.keys to return our test keys
            mock_cache_keys.side_effect = lambda pattern: [cache_key1, cache_key2] if pattern == f"storage:list:{self.test_bucket}:*" else []

            # Create a factory for the request
            factory = APIRequestFactory()

            # Create a request with the parameters in the request body (for DELETE)
            request = factory.delete(
                "/api/client/storage/delete/",
                {
                    "bucket_name": self.test_bucket,
                    "path": file_path
                },
                format="json"
            )

            # Add authentication to the request
            force_authenticate(request, user=self.user)

            # Call the view function directly
            response = delete_file(request)

            # Print response content for debugging
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.data if hasattr(response, 'data') else 'No data'}")

            # Verify the response
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, {"message": f"File '{file_path}' deleted successfully"})

            # Verify storage service was called with correct arguments
            mock_bucket.remove.assert_called_once_with([file_path])

            # Verify cache.keys was called with the correct pattern
            mock_cache_keys.assert_called_with(f"storage:list:{self.test_bucket}:*")

            # Verify cache.delete_many was called with our test keys
            mock_delete_many.assert_called_with([cache_key1, cache_key2])

        # After the test, the actual cache entries should still be there since we mocked delete_many
        self.assertEqual(cache.get(cache_key1), [{"data": "test1"}])
        self.assertEqual(cache.get(cache_key2), [{"data": "test2"}])
        self.assertEqual(cache.get(cache_key3), [{"data": "test3"}])

    def test_list_objects_performance(self):
        """Test performance improvement with caching."""
        # Import the view function directly
        from apps.users.views.client_view import list_objects
        
        # Mock storage service response (must be JSON serializable)
        mock_storage_response = [{"name": "file1.txt", "size": 1024}]
        
        # Create a factory for the request
        factory = APIRequestFactory()
        request_url = f"/api/client/storage/list/?bucket_name={self.test_bucket}&path={self.test_path}"
        
        # First request (cache miss) should be slower
        with patch('apps.users.views.client_view.supabase.get_storage_service') as mock_get_storage, \
             patch('apps.users.views.client_view.get_cached_result') as mock_cache_get:
            
            # Setup mock storage service
            mock_storage = MagicMock()
            mock_storage.list_objects.return_value = mock_storage_response
            mock_get_storage.return_value = mock_storage
            
            # Setup cache miss
            mock_cache_get.return_value = None
            
            # Create a request
            request1 = factory.get(request_url)
            
            # Add authentication to the request
            force_authenticate(request1, user=self.user)
            
            # Measure time for first request
            start_time = time.time()
            response1 = list_objects(request1)
            first_request_time = time.time() - start_time
            
            # Verify storage service was called
            mock_storage.list_objects.assert_called_once_with(self.test_bucket, self.test_path)
        
        # Generate expected cache key using SHA-256 hash, matching the implementation in the view
        path_hash = hashlib.sha256(self.test_path.encode()).hexdigest()
        cache_key = f"storage:list:{self.test_bucket}:{path_hash}"
        
        # Manually set cache for the second request
        cache.set(cache_key, mock_storage_response, timeout=300)
        
        # Second request (cache hit) should be faster
        with patch('apps.users.views.client_view.get_cached_result') as mock_cache_get:
            # Setup cache hit
            mock_cache_get.return_value = mock_storage_response
            
            # Create a new request
            request2 = factory.get(request_url)
            
            # Add authentication to the request
            force_authenticate(request2, user=self.user)
            
            # Measure time for second request
            start_time = time.time()
            response2 = list_objects(request2)
            second_request_time = time.time() - start_time
        
        # Verify second request was faster
        self.assertLess(second_request_time, first_request_time)
        
        # Verify both responses are successful
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
