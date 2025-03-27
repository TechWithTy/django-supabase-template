import pytest
from unittest.mock import patch, MagicMock, mock_open
import io

from ..storage import SupabaseStorageService


class TestSupabaseStorageService:
    """Tests for the SupabaseStorageService class"""

    @pytest.fixture
    def storage_service(self):
        """Create a SupabaseStorageService instance for testing"""
        with patch('apps.supabase.service.settings') as mock_settings:
            # Configure mock settings
            mock_settings.SUPABASE_DB_CONNECTION_STRING = 'https://example.supabase.co'
            mock_settings.SUPABASE_ANON_KEY = 'test-anon-key'
            mock_settings.SUPABASE_SERVICE_ROLE_KEY = 'test-service-role-key'
            
            storage_service = SupabaseStorageService()
            return storage_service
    
    @patch.object(SupabaseStorageService, '_make_request')
    def test_list_buckets(self, mock_make_request, storage_service):
        """Test listing storage buckets"""
        # Configure mock response
        mock_make_request.return_value = [
            {'id': 'bucket1', 'name': 'Bucket 1', 'public': True},
            {'id': 'bucket2', 'name': 'Bucket 2', 'public': False}
        ]
        
        # Call list_buckets method
        result = storage_service.list_buckets(auth_token='test-token')
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='GET',
            endpoint='/storage/v1/bucket',
            auth_token='test-token'
        )
        
        # Verify result
        assert len(result) == 2
        assert result[0]['id'] == 'bucket1'
        assert result[1]['name'] == 'Bucket 2'
    
    @patch.object(SupabaseStorageService, '_make_request')
    def test_create_bucket(self, mock_make_request, storage_service):
        """Test creating a storage bucket"""
        # Configure mock response
        mock_make_request.return_value = {
            'id': 'new-bucket',
            'name': 'New Bucket',
            'public': True
        }
        
        # Call create_bucket method
        result = storage_service.create_bucket(
            bucket_id='new-bucket',
            public=True,
            auth_token='test-token'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='POST',
            endpoint='/storage/v1/bucket',
            auth_token='test-token',
            data={
                'id': 'new-bucket',
                'name': 'new-bucket',
                'public': True
            }
        )
        
        # Verify result
        assert result['id'] == 'new-bucket'
        assert result['public'] is True
    
    @patch.object(SupabaseStorageService, '_make_request')
    def test_get_bucket(self, mock_make_request, storage_service):
        """Test getting a storage bucket"""
        # Configure mock response
        mock_make_request.return_value = {
            'id': 'test-bucket',
            'name': 'Test Bucket',
            'public': True
        }
        
        # Call get_bucket method
        result = storage_service.get_bucket(
            bucket_id='test-bucket',
            auth_token='test-token'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='GET',
            endpoint='/storage/v1/bucket/test-bucket',
            auth_token='test-token'
        )
        
        # Verify result
        assert result['id'] == 'test-bucket'
        assert result['name'] == 'Test Bucket'
    
    @patch.object(SupabaseStorageService, '_make_request')
    def test_update_bucket(self, mock_make_request, storage_service):
        """Test updating a storage bucket"""
        # Configure mock response
        mock_make_request.return_value = {
            'id': 'test-bucket',
            'name': 'Updated Bucket',
            'public': False
        }
        
        # Call update_bucket method
        result = storage_service.update_bucket(
            bucket_id='test-bucket',
            public=False,
            auth_token='test-token'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='PUT',
            endpoint='/storage/v1/bucket/test-bucket',
            auth_token='test-token',
            data={
                'id': 'test-bucket',
                'name': 'test-bucket',
                'public': False
            }
        )
        
        # Verify result
        assert result['id'] == 'test-bucket'
        assert result['public'] is False
    
    @patch.object(SupabaseStorageService, '_make_request')
    def test_empty_bucket(self, mock_make_request, storage_service):
        """Test emptying a storage bucket"""
        # Configure mock response
        mock_make_request.return_value = {}
        
        # Call empty_bucket method
        storage_service.empty_bucket(
            bucket_id='test-bucket',
            auth_token='test-token'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='POST',
            endpoint='/storage/v1/bucket/test-bucket/empty',
            auth_token='test-token'
        )
    
    @patch.object(SupabaseStorageService, '_make_request')
    def test_delete_bucket(self, mock_make_request, storage_service):
        """Test deleting a storage bucket"""
        # Configure mock response
        mock_make_request.return_value = {}
        
        # Call delete_bucket method
        storage_service.delete_bucket(
            bucket_id='test-bucket',
            auth_token='test-token'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='DELETE',
            endpoint='/storage/v1/bucket/test-bucket',
            auth_token='test-token'
        )
    
    @patch.object(SupabaseStorageService, '_make_request')
    def test_list_files(self, mock_make_request, storage_service):
        """Test listing files in a bucket"""
        # Configure mock response
        mock_make_request.return_value = {
            'items': [
                {'name': 'file1.txt', 'id': 'file1', 'size': 1024},
                {'name': 'file2.jpg', 'id': 'file2', 'size': 2048}
            ]
        }
        
        # Call list_files method
        result = storage_service.list_files(
            bucket_id='test-bucket',
            path='test-folder',
            auth_token='test-token'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='POST',
            endpoint='/storage/v1/object/list/test-bucket',
            auth_token='test-token',
            data={'prefix': 'test-folder'}
        )
        
        # Verify result
        assert len(result['items']) == 2
        assert result['items'][0]['name'] == 'file1.txt'
        assert result['items'][1]['size'] == 2048
    
    @patch.object(SupabaseStorageService, '_make_request')
    def test_upload_file(self, mock_make_request, storage_service):
        """Test uploading a file"""
        # Configure mock response
        mock_make_request.return_value = {
            'Key': 'test-bucket/test-file.txt'
        }
        
        # Create test file data
        file_data = io.BytesIO(b'Test file content')
        
        # Call upload_file method
        result = storage_service.upload_file(
            bucket_id='test-bucket',
            path='test-file.txt',
            file_data=file_data,
            content_type='text/plain',
            auth_token='test-token'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once()
        call_args = mock_make_request.call_args
        assert call_args[1]['method'] == 'POST'
        assert call_args[1]['endpoint'] == '/storage/v1/object/test-bucket/test-file.txt'
        assert call_args[1]['auth_token'] == 'test-token'
        assert call_args[1]['headers']['Content-Type'] == 'text/plain'
        
        # Verify result
        assert result['Key'] == 'test-bucket/test-file.txt'
    
    @patch.object(SupabaseStorageService, '_make_request')
    def test_download_file(self, mock_make_request, storage_service):
        """Test downloading a file"""
        # Configure mock response
        mock_response = MagicMock()
        mock_response.content = b'Test file content'
        mock_make_request.return_value = mock_response
        
        # Call download_file method
        result = storage_service.download_file(
            bucket_id='test-bucket',
            path='test-file.txt',
            auth_token='test-token'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='GET',
            endpoint='/storage/v1/object/test-bucket/test-file.txt',
            auth_token='test-token',
            return_raw=True
        )
        
        # Verify result
        assert result == b'Test file content'
    
    @patch.object(SupabaseStorageService, '_make_request')
    def test_get_public_url(self, mock_make_request, storage_service):
        """Test getting a public URL for a file"""
        # Call get_public_url method
        result = storage_service.get_public_url(
            bucket_id='test-bucket',
            path='test-file.txt'
        )
        
        # Verify result
        assert result == 'https://example.supabase.co/storage/v1/object/public/test-bucket/test-file.txt'
        
        # Verify no request was made
        mock_make_request.assert_not_called()
    
    @patch.object(SupabaseStorageService, '_make_request')
    def test_delete_file(self, mock_make_request, storage_service):
        """Test deleting a file"""
        # Configure mock response
        mock_make_request.return_value = {}
        
        # Call delete_file method
        storage_service.delete_file(
            bucket_id='test-bucket',
            paths=['test-file1.txt', 'test-file2.txt'],
            auth_token='test-token'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='POST',
            endpoint='/storage/v1/object/test-bucket',
            auth_token='test-token',
            data={'prefixes': ['test-file1.txt', 'test-file2.txt']}
        )
