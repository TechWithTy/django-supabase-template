import pytest
from django.urls import reverse
from rest_framework import status
import uuid
import base64


@pytest.mark.django_db
class TestStorageViews:
    """Integration tests for Supabase storage endpoints"""

    def test_list_buckets(self, authenticated_client, test_bucket):
        """Test listing storage buckets with real Supabase API"""
        # Skip if no test bucket available
        if not test_bucket:
            pytest.skip("No test bucket available")
            
        # Make request
        url = reverse('users:storage-list-buckets')
        response = authenticated_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert 'buckets' in response.data
        assert isinstance(response.data['buckets'], list)
        assert any(bucket['name'] == test_bucket for bucket in response.data['buckets'])
        
    def test_create_bucket(self, authenticated_client):
        """Test creating a storage bucket with real Supabase API"""
        # Generate a unique bucket name
        bucket_name = f"test-bucket-{uuid.uuid4().hex[:8]}"
        
        # Test data
        data = {
            'id': bucket_name,
            'public': True
        }
        
        # Make request
        url = reverse('users:storage-create-bucket')
        response = authenticated_client.post(url, data, format='json')
        
        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        assert 'bucket' in response.data
        assert response.data['bucket']['name'] == bucket_name
        
        # Clean up
        delete_url = reverse('users:storage-delete-bucket')
        authenticated_client.post(delete_url, {'id': bucket_name}, format='json')
        
    def test_list_files(self, authenticated_client, test_bucket, test_user_credentials, supabase_services):
        """Test listing files in a bucket with real Supabase API"""
        # Skip if no test bucket available
        if not test_bucket:
            pytest.skip("No test bucket available")
        
        # Upload a test file first
        storage_service = supabase_services['storage']
        auth_token = test_user_credentials['auth_token']
        
        # Create test file content
        test_content = b"This is a test file content for integration testing."
        test_file_path = f"test-file-{uuid.uuid4()}.txt"
        
        # Upload the test file
        storage_service.upload(
            bucket_id=test_bucket,
            file_path=test_file_path,
            file_content=test_content,
            content_type="text/plain",
            auth_token=auth_token
        )
        
        # Make request
        url = reverse('users:storage-list-files')
        response = authenticated_client.post(url, {'bucket_id': test_bucket}, format='json')
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert 'files' in response.data
        assert isinstance(response.data['files'], list)
        assert any(file['name'] == test_file_path for file in response.data['files'])
        
        # Clean up
        storage_service.delete(
            bucket_id=test_bucket,
            file_paths=[test_file_path],
            auth_token=auth_token
        )
        
    def test_upload_file(self, authenticated_client, test_bucket):
        """Test uploading a file with real Supabase API"""
        # Skip if no test bucket available
        if not test_bucket:
            pytest.skip("No test bucket available")
        
        # Generate a unique file name
        file_name = f"test-upload-{uuid.uuid4()}.txt"
        
        # Test data with base64 encoded file content
        file_content = "This is a test file content for integration testing."
        base64_content = base64.b64encode(file_content.encode()).decode()
        
        data = {
            'bucket_id': test_bucket,
            'file_path': file_name,
            'file_content': base64_content,
            'content_type': 'text/plain'
        }
        
        # Make request
        url = reverse('users:storage-upload-file')
        response = authenticated_client.post(url, data, format='json')
        
        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        assert 'key' in response.data
        assert response.data['key'] == file_name
        
        # Clean up
        delete_url = reverse('users:storage-delete-file')
        authenticated_client.post(
            delete_url, 
            {'bucket_id': test_bucket, 'file_paths': [file_name]}, 
            format='json'
        )
        
    def test_download_file(self, authenticated_client, test_bucket, test_user_credentials, supabase_services):
        """Test downloading a file with real Supabase API"""
        # Skip if no test bucket available
        if not test_bucket:
            pytest.skip("No test bucket available")
        
        # Upload a test file first
        storage_service = supabase_services['storage']
        auth_token = test_user_credentials['auth_token']
        
        # Create test file content
        test_content = b"This is a test file content for integration testing."
        test_file_path = f"test-download-{uuid.uuid4()}.txt"
        
        # Upload the test file
        storage_service.upload(
            bucket_id=test_bucket,
            file_path=test_file_path,
            file_content=test_content,
            content_type="text/plain",
            auth_token=auth_token
        )
        
        # Make request
        url = reverse('users:storage-download-file')
        response = authenticated_client.post(
            url, 
            {'bucket_id': test_bucket, 'file_path': test_file_path}, 
            format='json'
        )
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert 'data' in response.data
        assert response.data['content_type'] == 'text/plain'
        assert base64.b64decode(response.data['data']).decode() == test_content.decode()
        
        # Clean up
        storage_service.delete(
            bucket_id=test_bucket,
            file_paths=[test_file_path],
            auth_token=auth_token
        )
        
    def test_get_public_url(self, authenticated_client, test_bucket, test_user_credentials, supabase_services):
        """Test getting a public URL for a file with real Supabase API"""
        # Skip if no test bucket available
        if not test_bucket:
            pytest.skip("No test bucket available")
        
        # Upload a test file first
        storage_service = supabase_services['storage']
        auth_token = test_user_credentials['auth_token']
        
        # Create test file content
        test_content = b"This is a test file content for integration testing."
        test_file_path = f"test-public-url-{uuid.uuid4()}.txt"
        
        # Upload the test file
        storage_service.upload(
            bucket_id=test_bucket,
            file_path=test_file_path,
            file_content=test_content,
            content_type="text/plain",
            auth_token=auth_token
        )
        
        # Make request
        url = reverse('users:storage-get-public-url')
        response = authenticated_client.post(
            url, 
            {'bucket_id': test_bucket, 'file_path': test_file_path}, 
            format='json'
        )
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert 'publicURL' in response.data
        assert test_bucket in response.data['publicURL']
        assert test_file_path in response.data['publicURL']
        
        # Clean up
        storage_service.delete(
            bucket_id=test_bucket,
            file_paths=[test_file_path],
            auth_token=auth_token
        )
