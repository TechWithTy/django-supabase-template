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
            {"id": "bucket1", "name": "Bucket 1"},
            {"id": "bucket2", "name": "Bucket 2"},
        ]

        # Call list_buckets method
        result = storage_service.list_buckets(auth_token="test-token")

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="GET", 
            endpoint="/storage/v1/bucket", 
            auth_token="test-token",
            is_admin=False
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
            "name": "new-bucket",
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
            is_admin=True,
            data={"name": "new-bucket", "public": True},
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
            is_admin=False,
            data={},
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

    @pytest.mark.skipif(
        not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_ANON_KEY"),
        reason="Supabase credentials not set in environment variables",
    )
    def test_real_end_to_end_storage_flow(self, storage_service):
        """Comprehensive end-to-end test of all storage operations with real Supabase calls"""
        # Skip if not using --integration flag
        if os.getenv("SKIP_INTEGRATION_TESTS", "true").lower() == "true":
            pytest.skip("Integration tests disabled - use --integration flag to run")
        
        # Generate unique test identifiers
        test_bucket_name = f"test-bucket-{uuid.uuid4()}"
        test_file_1_path = f"test-file-1-{uuid.uuid4()}.txt"
        test_file_2_path = f"test-file-2-{uuid.uuid4()}.txt"
        test_file_3_path = f"test-file-3-{uuid.uuid4()}.json"
        test_nested_file_path = f"test-folder/nested-file-{uuid.uuid4()}.txt"
        test_move_destination = f"moved-file-{uuid.uuid4()}.txt"
        test_copy_destination = f"copied-file-{uuid.uuid4()}.txt"
        
        try:
            print(f"\nRunning end-to-end storage test with bucket: {test_bucket_name}")
            
            # 1. Create a bucket
            print("1. Creating bucket...")
            create_result = storage_service.create_bucket(
                bucket_id=test_bucket_name,
                public=True,
                file_size_limit=10 * 1024 * 1024,  # 10 MB
                allowed_mime_types=["image/jpeg", "image/png", "text/plain", "application/json"]
            )
            
            assert create_result is not None
            assert create_result["id"] == test_bucket_name
            assert create_result["public"] is True
            print("✓ Bucket created successfully")
            
            # 2. Get the bucket details
            print("2. Getting bucket details...")
            get_result = storage_service.get_bucket(
                bucket_id=test_bucket_name
            )
            
            assert get_result is not None
            assert get_result["id"] == test_bucket_name
            assert get_result["public"] is True
            print("✓ Bucket details retrieved successfully")
            
            # 3. Update the bucket
            print("3. Updating bucket...")
            update_result = storage_service.update_bucket(
                bucket_id=test_bucket_name,
                file_size_limit=5 * 1024 * 1024,  # 5 MB
            )
            
            assert update_result is not None
            assert update_result["id"] == test_bucket_name
            assert update_result["file_size_limit"] == 5 * 1024 * 1024
            print("✓ Bucket updated successfully")
            
            # 4. Upload multiple files
            print("4. Uploading files...")
            # Upload text file 1
            file_1_content = f"Test file 1 content {uuid.uuid4()}"
            file_1_data = io.BytesIO(file_1_content.encode())
            
            upload_result_1 = storage_service.upload_file(
                bucket_id=test_bucket_name,
                path=test_file_1_path,
                file_data=file_1_data,
                content_type="text/plain"
            )
            
            assert upload_result_1 is not None
            
            # Upload text file 2
            file_2_content = f"Test file 2 content {uuid.uuid4()}"
            file_2_data = io.BytesIO(file_2_content.encode())
            
            upload_result_2 = storage_service.upload_file(
                bucket_id=test_bucket_name,
                path=test_file_2_path,
                file_data=file_2_data,
                content_type="text/plain"
            )
            
            assert upload_result_2 is not None
            
            # Upload JSON file
            json_content = f'{{"test": "data", "id": "{uuid.uuid4()}", "timestamp": "{uuid.uuid4()}"}}'.encode()
            json_data = io.BytesIO(json_content)
            
            upload_result_3 = storage_service.upload_file(
                bucket_id=test_bucket_name,
                path=test_file_3_path,
                file_data=json_data,
                content_type="application/json"
            )
            
            assert upload_result_3 is not None
            
            # Upload a file in a nested folder
            nested_file_content = f"Nested file content {uuid.uuid4()}"
            nested_file_data = io.BytesIO(nested_file_content.encode())
            
            upload_result_4 = storage_service.upload_file(
                bucket_id=test_bucket_name,
                path=test_nested_file_path,
                file_data=nested_file_data,
                content_type="text/plain"
            )
            
            assert upload_result_4 is not None
            print("✓ Files uploaded successfully")
            
            # 5. List files
            print("5. Listing files...")
            list_result = storage_service.list_files(
                bucket_id=test_bucket_name
            )
            
            assert list_result is not None
            assert "items" in list_result
            assert len(list_result["items"]) >= 4  # At least our 4 files
            
            # Verify all our files are in the list
            file_names = [file["name"] for file in list_result["items"]]
            assert test_file_1_path in file_names
            assert test_file_2_path in file_names
            assert test_file_3_path in file_names
            assert test_nested_file_path in file_names
            print("✓ Files listed successfully")
            
            # 6. Get public URLs
            print("6. Getting public URLs...")
            public_url_1 = storage_service.get_public_url(
                bucket_id=test_bucket_name,
                path=test_file_1_path
            )
            
            assert public_url_1 is not None
            assert test_bucket_name in public_url_1
            assert test_file_1_path in public_url_1
            print("✓ Public URL generated successfully")
            
            # 7. Create signed URL
            print("7. Creating signed URL...")
            signed_url = storage_service.create_signed_url(
                bucket_id=test_bucket_name,
                path=test_file_2_path,
                expires_in=60  # 60 seconds
            )
            
            assert signed_url is not None
            assert "token" in signed_url
            assert "signedURL" in signed_url
            print("✓ Signed URL created successfully")
            
            # 8. Download a file
            print("8. Downloading file...")
            downloaded_content = storage_service.download_file(
                bucket_id=test_bucket_name,
                path=test_file_1_path
            )
            
            assert downloaded_content is not None
            assert downloaded_content.decode() == file_1_content
            print("✓ File downloaded successfully")
            
            # 9. Move a file
            print("9. Moving file...")
            move_result = storage_service.move_file(
                bucket_id=test_bucket_name,
                source_path=test_file_2_path,
                destination_path=test_move_destination
            )
            
            assert move_result is not None
            print("✓ File moved successfully")
            
            # 10. Copy a file
            print("10. Copying file...")
            copy_result = storage_service.copy_file(
                bucket_id=test_bucket_name,
                source_path=test_file_1_path,
                destination_path=test_copy_destination
            )
            
            assert copy_result is not None
            print("✓ File copied successfully")
            
            # 11. List files again to verify move and copy operations
            print("11. Verifying move and copy operations...")
            list_result_after = storage_service.list_files(
                bucket_id=test_bucket_name
            )
            
            file_names_after = [file["name"] for file in list_result_after["items"]]
            assert test_file_1_path in file_names_after  # Original still exists
            assert test_move_destination in file_names_after  # Moved file exists
            assert test_copy_destination in file_names_after  # Copied file exists
            assert test_file_2_path not in file_names_after  # Original of moved file is gone
            print("✓ Move and copy operations verified")
            
            # 12. Create a signed upload URL
            print("12. Creating signed upload URL...")
            signed_upload_url = storage_service.create_signed_upload_url(
                bucket_id=test_bucket_name,
                path=f"signed-upload-{uuid.uuid4()}.txt"
            )
            
            assert signed_upload_url is not None
            assert "token" in signed_upload_url
            assert "signedURL" in signed_upload_url
            print("✓ Signed upload URL created successfully")
            
            # 13. Delete individual files
            print("13. Deleting individual files...")
            delete_result = storage_service.delete_file(
                bucket_id=test_bucket_name,
                paths=[test_file_1_path, test_move_destination]
            )
            
            assert delete_result is not None
            print("✓ Files deleted successfully")
            
            # 14. Empty the bucket
            print("14. Emptying bucket...")
            empty_result = storage_service.empty_bucket(
                bucket_id=test_bucket_name
            )
            
            assert empty_result is not None
            print("✓ Bucket emptied successfully")
            
            # 15. Verify bucket is empty
            print("15. Verifying bucket is empty...")
            list_result_empty = storage_service.list_files(
                bucket_id=test_bucket_name
            )
            
            assert list_result_empty is not None
            assert "items" in list_result_empty
            assert len(list_result_empty["items"]) == 0
            print("✓ Bucket is empty")
            
            # 16. Delete the bucket
            print("16. Deleting bucket...")
            delete_bucket_result = storage_service.delete_bucket(
                bucket_id=test_bucket_name
            )
            
            assert delete_bucket_result is not None
            print("✓ Bucket deleted successfully")
            
            # 17. Verify bucket is deleted by listing all buckets
            print("17. Verifying bucket deletion...")
            list_buckets_result = storage_service.list_buckets()
            
            bucket_ids = [bucket["id"] for bucket in list_buckets_result]
            assert test_bucket_name not in bucket_ids
            print("✓ Bucket deletion verified")
            
            print("\n✓✓✓ End-to-end storage test completed successfully ✓✓✓")
            
        except Exception as e:
            # Clean up resources even if test fails
            print(f"\n❌ Test failed: {str(e)}")
            try:
                # Try to clean up any remaining files
                storage_service.empty_bucket(bucket_id=test_bucket_name)
                # Try to delete the bucket
                storage_service.delete_bucket(bucket_id=test_bucket_name)
                print("✓ Cleanup completed after test failure")
            except Exception as cleanup_error:
                print(f"❌ Cleanup failed: {str(cleanup_error)}")
            
            # Re-raise the original exception
            pytest.fail(f"Real-world end-to-end storage test failed: {str(e)}")
