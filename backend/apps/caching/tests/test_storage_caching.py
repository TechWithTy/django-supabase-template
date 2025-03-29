import time
import hashlib
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
        
        # First call should cache the result
        with patch('apps.users.views.client_view.supabase.get_storage_service') as mock_storage_service, \
             patch('apps.users.views.client_view.get_cached_result') as mock_cache_get, \
             patch('apps.users.views.client_view.cache.set') as mock_cache_set:
            
            # Setup mock storage service
            mock_storage = MagicMock()
            mock_storage.list_objects.return_value = [{"name": "file1.txt", "size": 1024}]
            mock_storage_service.return_value = mock_storage
            
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
            self.assertEqual(response1.data, mock_storage.list_objects.return_value)
    
    def test_list_objects_cache_hit(self):
        """Test that list_objects returns cached data on cache hit."""
        # Import the view function directly
        from apps.users.views.client_view import list_objects
        
        # Generate expected cache key
        path_hash = hashlib.md5(self.test_path.encode()).hexdigest()
        cache_key = f"storage:list:{self.test_bucket}:{path_hash}"
        
        # Manually set cache with mock data
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
        with patch('apps.users.views.client_view.supabase.get_storage_service') as mock_storage_service:
            # Call the view function directly
            response = list_objects(request)
            
            # Verify storage service was not called (cache hit)
            mock_storage_service.assert_not_called()
            
            # Verify response contains cached data
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
        file_data = "base64encodeddata"  # In real scenario, this would be base64 encoded
        
        # Import the view function directly
        from apps.users.views.client_view import upload_file
        
        # Call upload_file with mocked storage service
        with patch('apps.users.views.client_view.supabase.get_storage_service') as mock_storage_service, \
             patch.object(cache, 'keys', create=True) as mock_cache_keys, \
             patch.object(cache, 'delete_many') as mock_delete_many:
            
            # Setup mock storage service
            mock_storage = MagicMock()
            mock_storage.upload_file.return_value = {"message": "File uploaded"}
            mock_storage_service.return_value = mock_storage
            
            # Setup mock cache.keys to return our test keys
            mock_cache_keys.side_effect = lambda pattern: [cache_key1, cache_key2] if pattern == f"storage:list:{self.test_bucket}:*" else []
            
            # Create a factory for the request
            factory = APIRequestFactory()
            
            # Create a request with the correct parameters
            request = factory.post(
                "/api/client/storage/upload/",
                {
                    "bucket_name": self.test_bucket,
                    "file_path": self.test_path,
                    "file_data": file_data  # Changed from 'file' to 'file_data'
                },
                format="json"  # Changed from 'multipart' to 'json'
            )
            
            # Add authentication to the request
            force_authenticate(request, user=self.user)
            
            # Call the view function directly
            response = upload_file(request)
            
            # Verify response contains correct data
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, {"message": "File uploaded"})
            
            # Verify storage service was called with correct arguments
            mock_storage.upload_file.assert_called_once_with(self.test_bucket, self.test_path, file_data)
            
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
        with patch('apps.users.views.client_view.supabase.get_storage_service') as mock_storage_service, \
             patch.object(cache, 'keys', create=True) as mock_cache_keys, \
             patch.object(cache, 'delete_many') as mock_delete_many:
            
            # Setup mock storage service
            mock_storage = MagicMock()
            mock_storage.delete_file.return_value = {"message": "File deleted"}
            mock_storage_service.return_value = mock_storage
            
            # Setup mock cache.keys to return our test keys
            mock_cache_keys.side_effect = lambda pattern: [cache_key1, cache_key2] if pattern == f"storage:list:{self.test_bucket}:*" else []
            
            # Create a factory for the request
            factory = APIRequestFactory()
            
            # Create a request with the necessary query parameters
            request = factory.delete(
                f"/api/client/storage/delete/?bucket_name={self.test_bucket}&file_path={file_path}"
            )
            
            # Add authentication to the request
            force_authenticate(request, user=self.user)
            
            # Call the view function directly
            response = delete_file(request)
            
            # Verify the response
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, {"message": "File deleted"})
            
            # Verify storage service was called with correct arguments
            mock_storage.delete_file.assert_called_once_with(self.test_bucket, file_path)
            
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
        
        # Mock storage service response
        mock_storage_response = [{"name": "file1.txt", "size": 1024}]
        
        # Create a factory for the request
        factory = APIRequestFactory()
        request_url = f"/api/client/storage/list/?bucket_name={self.test_bucket}&path={self.test_path}"
        
        # First request (cache miss) should be slower
        with patch('apps.users.views.client_view.supabase.get_storage_service') as mock_storage_service, \
             patch('apps.users.views.client_view.get_cached_result') as mock_cache_get:
            
            # Setup mock storage service
            mock_storage = MagicMock()
            mock_storage.list_objects.return_value = mock_storage_response
            mock_storage_service.return_value = mock_storage
            
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
