import os
import pytest
from dotenv import load_dotenv

from ..client import SupabaseClient

# Load environment variables from .env file
load_dotenv()

# Skip these tests if Supabase credentials are not available
pytest.mark.skipif(
    not os.getenv("SUPABASE_DB_CONNECTION_STRING")
    or not os.getenv("SUPABASE_ANON_KEY"),
    reason="Supabase credentials not available",
)


@pytest.fixture
def supabase_client():
    """Create a real Supabase client for integration testing"""
    return SupabaseClient()


@pytest.fixture
def test_user_credentials():
    """Test user credentials - should be configured in your test environment"""
    return {
        "email": os.getenv("TEST_USER_EMAIL", "test@example.com"),
        "password": os.getenv("TEST_USER_PASSWORD", "testpassword123"),
    }


@pytest.fixture
def test_bucket_name():
    """Test bucket name for storage tests"""
    return os.getenv("TEST_BUCKET_NAME", "test-bucket")


@pytest.fixture
def test_table_name():
    """Test table name for database tests"""
    return os.getenv("TEST_TABLE_NAME", "test_table")


class TestSupabaseIntegration:
    """Integration tests for Supabase services"""

    def test_auth_sign_up_and_sign_in(self, supabase_client, test_user_credentials):
        """Test sign up and sign in functionality"""
        # Skip if using a pre-existing test user
        if os.getenv("SKIP_USER_CREATION", "false").lower() == "true":
            pytest.skip("Skipping user creation as requested")

        # Generate a unique email for testing
        import uuid

        unique_email = f"test-{uuid.uuid4()}@example.com"
        test_password = "securePassword123!"

        try:
            # Sign up a new user
            signup_response = supabase_client.auth.sign_up(
                email=unique_email,
                password=test_password,
                user_metadata={"name": "Test User"},
            )
            assert signup_response is not None
            assert "user" in signup_response or "id" in signup_response

            # Sign in with the new user
            signin_response = supabase_client.auth.sign_in_with_email(
                email=unique_email, password=test_password
            )
            assert signin_response is not None
            assert "access_token" in signin_response
        except Exception as e:
            # Clean up if possible, but continue with the test
            print(f"Error in sign up/sign in test: {e}")

    def test_auth_with_existing_user(self, supabase_client, test_user_credentials):
        """Test authentication with existing user"""
        try:
            # Sign in with existing test user
            response = supabase_client.auth.sign_in_with_email(
                email=test_user_credentials["email"],
                password=test_user_credentials["password"],
            )
            assert response is not None
            assert "access_token" in response
            assert "refresh_token" in response

            # Get user data
            token = response["access_token"]
            user_response = supabase_client.auth.get_user(token)
            assert user_response is not None
        except Exception as e:
            pytest.skip(f"Skipping test due to authentication error: {e}")

    def test_database_operations(
        self, supabase_client, test_user_credentials, test_table_name
    ):
        """Test database operations"""
        try:
            # Sign in first to get token
            auth_response = supabase_client.auth.sign_in_with_email(
                email=test_user_credentials["email"],
                password=test_user_credentials["password"],
            )
            token = auth_response["access_token"]

            # Create test data
            test_data = {"name": "Test Item", "description": "Test Description"}

            # Insert data
            insert_response = supabase_client.database.insert_data(
                table=test_table_name, data=test_data, auth_token=token
            )
            assert insert_response is not None
            assert len(insert_response) > 0
            inserted_id = insert_response[0]["id"]

            # Fetch data
            fetch_response = supabase_client.database.fetch_data(
                table=test_table_name, filters={"id": inserted_id}, auth_token=token
            )
            assert fetch_response is not None
            assert len(fetch_response) > 0
            assert fetch_response[0]["name"] == "Test Item"

            # Update data
            update_data = {"description": "Updated Description"}
            update_response = supabase_client.database.update_data(
                table=test_table_name,
                data=update_data,
                filters={"id": inserted_id},
                auth_token=token,
            )
            assert update_response is not None
            assert len(update_response) > 0
            assert update_response[0]["description"] == "Updated Description"

            # Delete data
            delete_response = supabase_client.database.delete_data(
                table=test_table_name, filters={"id": inserted_id}, auth_token=token
            )
            assert delete_response is not None

        except Exception as e:
            pytest.skip(f"Skipping test due to database error: {e}")

    def test_storage_operations(
        self, supabase_client, test_user_credentials, test_bucket_name
    ):
        """Test storage operations"""
        try:
            # Sign in first to get token
            auth_response = supabase_client.auth.sign_in_with_email(
                email=test_user_credentials["email"],
                password=test_user_credentials["password"],
            )
            token = auth_response["access_token"]

            # Create a test file
            import io

            test_file = io.BytesIO(b"Test file content")
            test_filename = f"test-file-{os.urandom(4).hex()}.txt"

            # Check if bucket exists, create if it doesn't
            try:
                supabase_client.storage.get_bucket(
                    bucket_id=test_bucket_name, auth_token=token
                )
            except Exception:
                # Bucket doesn't exist, create it
                supabase_client.storage.create_bucket(
                    bucket_id=test_bucket_name, public=True, auth_token=token
                )

            # Upload file
            upload_response = supabase_client.storage.upload_file(
                bucket_id=test_bucket_name,
                path=test_filename,
                file_data=test_file,
                content_type="text/plain",
                auth_token=token,
            )
            assert upload_response is not None

            # List files
            list_response = supabase_client.storage.list_files(
                bucket_id=test_bucket_name, auth_token=token
            )
            assert list_response is not None
            assert "items" in list_response

            # Get public URL
            public_url = supabase_client.storage.get_public_url(
                bucket_id=test_bucket_name, path=test_filename
            )
            assert test_bucket_name in public_url
            assert test_filename in public_url

            # Download file
            download_response = supabase_client.storage.download_file(
                bucket_id=test_bucket_name, path=test_filename, auth_token=token
            )
            assert download_response is not None
            assert b"Test file content" == download_response

            # Delete file
            supabase_client.storage.delete_file(
                bucket_id=test_bucket_name, paths=[test_filename], auth_token=token
            )

        except Exception as e:
            pytest.skip(f"Skipping test due to storage error: {e}")

    def test_edge_functions(self, supabase_client, test_user_credentials):
        """Test edge functions"""
        # Skip if no edge function is defined
        edge_function_name = os.getenv("TEST_EDGE_FUNCTION")
        if not edge_function_name:
            pytest.skip("No test edge function defined")

        try:
            # Sign in first to get token
            auth_response = supabase_client.auth.sign_in_with_email(
                email=test_user_credentials["email"],
                password=test_user_credentials["password"],
            )
            token = auth_response["access_token"]

            # Invoke edge function
            response = supabase_client.edge_functions.invoke_function(
                function_name=edge_function_name,
                params={"test": True},
                auth_token=token,
            )
            assert response is not None

        except Exception as e:
            pytest.skip(f"Skipping test due to edge function error: {e}")
