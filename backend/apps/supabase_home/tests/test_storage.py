import pytest
import os
import uuid
from unittest.mock import patch, MagicMock
import io

from ..storage import SupabaseStorageService


class TestSupabaseStorageService:
    """Tests for the SupabaseStorageService class"""

    @pytest.fixture
    def mock_settings(self):
        """Mock Django settings"""
        with patch("apps.supabase_home._service.settings") as mock_settings:
            # Configure mock settings
            mock_settings.SUPABASE_URL = "https://example.supabase.co"
            mock_settings.SUPABASE_ANON_KEY = "test-anon-key"
            mock_settings.SUPABASE_SERVICE_ROLE_KEY = "test-service-role-key"
            yield mock_settings

    @pytest.fixture
    def storage_service(self, mock_settings):
        """Create a SupabaseStorageService instance for testing"""
        return SupabaseStorageService()

    @patch.object(SupabaseStorageService, "_make_request")
    def test_list_buckets(self, mock_make_request, storage_service):
        """Test listing storage buckets"""
        # Configure mock response
        mock_make_request.return_value = [
            {"id": "bucket1", "name": "Bucket 1", "public": True},
            {"id": "bucket2", "name": "Bucket 2", "public": False},
        ]

        # Call list_buckets method
        result = storage_service.list_buckets(auth_token="test-token")

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="GET", endpoint="/storage/v1/bucket", auth_token="test-token"
        )

        # Verify result
        assert len(result) == 2
        assert result[0]["id"] == "bucket1"
        assert result[1]["name"] == "Bucket 2"

    @patch.object(SupabaseStorageService, "_make_request")
    def test_create_bucket(self, mock_make_request, storage_service):
        """Test creating a storage bucket"""
        # Configure mock response
        mock_make_request.return_value = {
            "id": "new-bucket",
            "name": "New Bucket",
            "public": True,
        }

        # Call create_bucket method
        result = storage_service.create_bucket(
            bucket_id="new-bucket", public=True, auth_token="test-token"
        )

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/storage/v1/bucket",
            auth_token="test-token",
            data={"id": "new-bucket", "public": True},
        )

        # Verify result
        assert result["id"] == "new-bucket"
        assert result["public"] is True

    @patch.object(SupabaseStorageService, "_make_request")
    def test_get_bucket(self, mock_make_request, storage_service):
        """Test getting a storage bucket"""
        # Configure mock response
        mock_make_request.return_value = {
            "id": "test-bucket",
            "name": "Test Bucket",
            "public": True,
        }

        # Call get_bucket method
        result = storage_service.get_bucket(
            bucket_id="test-bucket", auth_token="test-token"
        )

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="GET",
            endpoint="/storage/v1/bucket/test-bucket",
            auth_token="test-token",
        )

        # Verify result
        assert result["id"] == "test-bucket"
        assert result["name"] == "Test Bucket"

    @patch.object(SupabaseStorageService, "_make_request")
    def test_update_bucket(self, mock_make_request, storage_service):
        """Test updating a storage bucket"""
        # Configure mock response
        mock_make_request.return_value = {
            "id": "test-bucket",
            "name": "Updated Bucket",
            "public": False,
        }

        # Call update_bucket method
        result = storage_service.update_bucket(
            bucket_id="test-bucket", public=False, auth_token="test-token"
        )

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="PUT",
            endpoint="/storage/v1/bucket/test-bucket",
            auth_token="test-token",
            data={"public": False},
        )

        # Verify result
        assert result["id"] == "test-bucket"
        assert result["name"] == "Updated Bucket"
        assert result["public"] is False

    @patch.object(SupabaseStorageService, "_make_request")
    def test_empty_bucket(self, mock_make_request, storage_service):
        """Test emptying a storage bucket"""
        # Configure mock response
        mock_make_request.return_value = {}

        # Call empty_bucket method
        storage_service.empty_bucket(bucket_id="test-bucket", auth_token="test-token")

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/storage/v1/bucket/test-bucket/empty",
            auth_token="test-token",
        )

    @patch.object(SupabaseStorageService, "_make_request")
    def test_delete_bucket(self, mock_make_request, storage_service):
        """Test deleting a storage bucket"""
        # Configure mock response
        mock_make_request.return_value = {}

        # Call delete_bucket method
        storage_service.delete_bucket(bucket_id="test-bucket", auth_token="test-token")

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="DELETE",
            endpoint="/storage/v1/bucket/test-bucket",
            auth_token="test-token",
        )

    @patch.object(SupabaseStorageService, "_make_request")
    def test_list_files(self, mock_make_request, storage_service):
        """Test listing files in a bucket"""
        # Configure mock response
        mock_make_request.return_value = {
            "items": [
                {"name": "file1.txt", "id": "file1", "size": 1024},
                {"name": "file2.jpg", "id": "file2", "size": 2048},
            ]
        }

        # Call list_files method
        result = storage_service.list_files(
            bucket_id="test-bucket", path="test-folder", auth_token="test-token"
        )

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/storage/v1/object/list/test-bucket",
            auth_token="test-token",
            data={"prefix": "test-folder", "limit": 100, "offset": 0},
        )

        # Verify result
        assert len(result["items"]) == 2
        assert result["items"][0]["name"] == "file1.txt"
        assert result["items"][1]["size"] == 2048

    @patch("requests.post")
    def test_upload_file(self, mock_post, storage_service):
        """Test uploading a file"""
        # Configure mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"Key": "test-bucket/test-file.txt"}
        mock_post.return_value = mock_response

        # Create test file data
        file_data = io.BytesIO(b"Test file content")

        # Call upload_file method
        result = storage_service.upload_file(
            bucket_id="test-bucket",
            path="test-file.txt",
            file_data=file_data,
            content_type="text/plain",
            auth_token="test-token",
        )

        # Verify result
        assert result["Key"] == "test-bucket/test-file.txt"


class TestRealSupabaseStorageService:
    """Real-world integration tests for SupabaseStorageService
    
    These tests make actual API calls to Supabase and require:
    1. A valid Supabase URL and API keys in env variables
    2. Use of the --integration flag when running tests
    """
    
    @pytest.fixture
    def storage_service(self):
        """Create a real SupabaseStorageService instance"""
        return SupabaseStorageService()

    @pytest.fixture
    def test_bucket_name(self):
        """Generate a unique test bucket name or use from environment"""
        return os.getenv("TEST_BUCKET_NAME", f"test-bucket-{uuid.uuid4()}")
    
    @pytest.fixture
    def test_file_path(self):
        """Generate a unique test file path"""
        return f"test-file-{uuid.uuid4()}.txt"
    
    @pytest.mark.skipif(
        not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_ANON_KEY"),
        reason="Supabase credentials not set in environment variables",
    )
    def test_real_bucket_operations(self, storage_service, test_bucket_name):
        """Test bucket CRUD operations with real Supabase"""
        # Skip if not using --integration flag
        if os.getenv("SKIP_INTEGRATION_TESTS", "true").lower() == "true":
            pytest.skip("Integration tests disabled - use --integration flag to run")
        
        try:
            # 1. Create a bucket
            create_result = storage_service.create_bucket(
                bucket_id=test_bucket_name,
                public=True
            )
            
            assert create_result is not None
            assert create_result["id"] == test_bucket_name
            
            # 2. Get the bucket
            get_result = storage_service.get_bucket(
                bucket_id=test_bucket_name
            )
            
            assert get_result is not None
            assert get_result["id"] == test_bucket_name
            assert get_result["public"] is True
            
            # 3. Update the bucket
            update_result = storage_service.update_bucket(
                bucket_id=test_bucket_name,
                public=False
            )
            
            assert update_result is not None
            assert update_result["id"] == test_bucket_name
            assert update_result["public"] is False
            
            # 4. List buckets and ensure our bucket is there
            list_result = storage_service.list_buckets()
            
            assert list_result is not None
            assert any(bucket["id"] == test_bucket_name for bucket in list_result)
            
            # 5. Clean up - delete the bucket
            storage_service.delete_bucket(bucket_id=test_bucket_name)
            
            # 6. Verify deletion
            list_result_after = storage_service.list_buckets()
            assert not any(bucket["id"] == test_bucket_name for bucket in list_result_after)
            
        except Exception as e:
            # Make sure to clean up even if test fails
            try:
                storage_service.delete_bucket(bucket_id=test_bucket_name)
            except Exception as e:
                pytest.fail(f"Failed to clean up bucket: {str(e)}")
            pytest.fail(f"Real-world Supabase storage bucket test failed: {str(e)}")
    
    @pytest.mark.skipif(
        not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_ANON_KEY"),
        reason="Supabase credentials not set in environment variables",
    )
    def test_real_file_operations(self, storage_service, test_bucket_name, test_file_path):
        """Test file operations with real Supabase"""
        # Skip if not using --integration flag
        if os.getenv("SKIP_INTEGRATION_TESTS", "true").lower() == "true":
            pytest.skip("Integration tests disabled - use --integration flag to run")
        
        try:
            # 0. Create bucket for testing
            try:
                storage_service.create_bucket(
                    bucket_id=test_bucket_name,
                    public=True
                )
            except Exception as e:
                if "already exists" not in str(e).lower():
                    raise
            
            # 1. Upload a file
            file_content = f"Test file content {uuid.uuid4()}"
            file_data = io.BytesIO(file_content.encode())
            
            upload_result = storage_service.upload_file(
                bucket_id=test_bucket_name,
                path=test_file_path,
                file_data=file_data,
                content_type="text/plain"
            )
            
            assert upload_result is not None
            
            # 2. List files and check if our file is there
            list_result = storage_service.list_files(
                bucket_id=test_bucket_name
            )
            
            assert list_result is not None
            assert "items" in list_result
            assert any(file["name"] == test_file_path for file in list_result["items"])
            
            # 3. Get a public URL for the file
            public_url = storage_service.get_public_url(
                bucket_id=test_bucket_name,
                path=test_file_path
            )
            
            assert public_url is not None
            assert test_bucket_name in public_url
            assert test_file_path in public_url
            
            # 4. Clean up - delete the file
            storage_service.delete_file(
                bucket_id=test_bucket_name,
                paths=[test_file_path]
            )
            
            # 5. Verify deletion
            list_result_after = storage_service.list_files(
                bucket_id=test_bucket_name
            )
            assert not any(file["name"] == test_file_path for file in list_result_after["items"])
            
        except Exception as e:
            # Clean up even if test fails
            try:
                storage_service.delete_file(
                    bucket_id=test_bucket_name,
                    paths=[test_file_path]
                )
            except Exception as e:
                pytest.fail(f"Failed to clean up file: {str(e)}")
            pytest.fail(f"Real-world Supabase storage file test failed: {str(e)}")
        finally:
            # Try to delete the test bucket
            try:
                storage_service.empty_bucket(bucket_id=test_bucket_name)
                storage_service.delete_bucket(bucket_id=test_bucket_name)
            except Exception as e:
                pytest.fail(f"Failed to clean up bucket: {str(e)}")
