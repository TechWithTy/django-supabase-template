import pytest
import os
import uuid
from unittest.mock import patch

from ..auth import SupabaseAuthService


class TestSupabaseAuthService:
    """Tests for the SupabaseAuthService class"""

    @pytest.fixture
    def mock_settings(self):
        """Mock Django settings"""
        with patch(" apps.supabase_home._service.settings") as mock_settings:
            # Configure mock settings
            mock_settings.SUPABASE_URL = "https://example.supabase.co"
            mock_settings.SUPABASE_ANON_KEY = "test-anon-key"
            mock_settings.SUPABASE_SERVICE_ROLE_KEY = "test-service-role-key"
            yield mock_settings

    @pytest.fixture
    def auth_service(self, mock_settings):
        """Create a SupabaseAuthService instance for testing"""
        return SupabaseAuthService()

    @patch.object(SupabaseAuthService, "_make_request")
    def test_sign_up(self, mock_make_request, auth_service):
        """Test signing up a new user"""
        # Configure mock response
        mock_make_request.return_value = {
            "id": "user-id",
            "email": "test@example.com",
            "app_metadata": {},
            "user_metadata": {"name": "Test User"},
            "created_at": "2023-01-01T00:00:00Z",
        }

        # Call sign_up method
        result = auth_service.sign_up(
            email="test@example.com",
            password="password123",
            user_metadata={"name": "Test User"},
        )

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/auth/v1/signup",
            data={
                "email": "test@example.com",
                "password": "password123",
                "data": {"name": "Test User"},
            },
        )

        # Verify result
        assert result["id"] == "user-id"
        assert result["email"] == "test@example.com"

    @patch.object(SupabaseAuthService, "_make_request")
    def test_sign_in_with_email(self, mock_make_request, auth_service):
        """Test signing in with email and password"""
        # Configure mock response
        mock_make_request.return_value = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "user": {"id": "user-id", "email": "test@example.com"},
        }

        # Call sign_in_with_email method
        result = auth_service.sign_in_with_email(
            email="test@example.com", password="password123"
        )

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/auth/v1/token",
            data={
                "email": "test@example.com",
                "password": "password123",
                "grant_type": "password",
            },
        )

        # Verify result
        assert result["access_token"] == "test-access-token"
        assert result["refresh_token"] == "test-refresh-token"
        assert result["user"]["id"] == "user-id"

    @patch.object(SupabaseAuthService, "_make_request")
    def test_sign_out(self, mock_make_request, auth_service):
        """Test signing out a user"""
        # Configure mock response
        mock_make_request.return_value = {}

        # Call sign_out method
        auth_service.sign_out(auth_token="test-token")

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="POST", endpoint="/auth/v1/logout", auth_token="test-token"
        )

    @patch.object(SupabaseAuthService, "_make_request")
    def test_get_user(self, mock_make_request, auth_service):
        """Test getting user data"""
        # Configure mock response
        mock_make_request.return_value = {
            "id": "user-id",
            "email": "test@example.com",
            "app_metadata": {},
            "user_metadata": {"name": "Test User"},
        }

        # Call get_user method
        result = auth_service.get_user(auth_token="test-token")

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="GET", endpoint="/auth/v1/user", auth_token="test-token"
        )

        # Verify result
        assert result["id"] == "user-id"
        assert result["email"] == "test@example.com"

    @patch.object(SupabaseAuthService, "_make_request")
    def test_update_user(self, mock_make_request, auth_service):
        """Test updating user data"""
        # Configure mock response
        mock_make_request.return_value = {
            "id": "user-id",
            "email": "test@example.com",
            "user_metadata": {"name": "Updated Name"},
        }

        # Call update_user method
        result = auth_service.update_user(
            auth_token="test-token", user_metadata={"name": "Updated Name"}
        )

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="PUT",
            endpoint="/auth/v1/user",
            auth_token="test-token",
            data={"data": {"name": "Updated Name"}},
        )

        # Verify result
        assert result["id"] == "user-id"
        assert result["user_metadata"]["name"] == "Updated Name"

    @patch.object(SupabaseAuthService, "_make_request")
    def test_create_user(self, mock_make_request, auth_service):
        """Test creating a user as admin"""
        # Configure mock response
        mock_make_request.return_value = {
            "id": "user-id",
            "email": "test@example.com",
            "user_metadata": {"name": "Test User"},
        }

        # Call create_user method
        result = auth_service.create_user(
            email="test@example.com",
            password="password123",
            user_metadata={"name": "Test User"},
        )

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/auth/v1/admin/users",
            is_admin=True,
            data={
                "email": "test@example.com",
                "password": "password123",
                "user_metadata": {"name": "Test User"},
            },
        )

        # Verify result
        assert result["id"] == "user-id"
        assert result["email"] == "test@example.com"

    @patch.object(SupabaseAuthService, "_make_request")
    def test_refresh_token(self, mock_make_request, auth_service):
        """Test refreshing authentication token"""
        # Configure mock response
        mock_make_request.return_value = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "user": {"id": "user-id", "email": "test@example.com"},
        }

        # Call refresh_token method
        result = auth_service.refresh_token(refresh_token="old-refresh-token")

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/auth/v1/token",
            data={"refresh_token": "old-refresh-token", "grant_type": "refresh_token"},
        )

        # Verify result
        assert result["access_token"] == "new-access-token"
        assert result["refresh_token"] == "new-refresh-token"

    @patch.object(SupabaseAuthService, "_make_request")
    def test_reset_password_for_email(self, mock_make_request, auth_service):
        """Test sending password reset email"""
        # Configure mock response
        mock_make_request.return_value = {}

        # Call reset_password_for_email method
        auth_service.reset_password_for_email(email="test@example.com")

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/auth/v1/recover",
            data={"email": "test@example.com"},
        )

    @patch.object(SupabaseAuthService, "_make_request")
    def test_get_user_error_handling(self, mock_make_request, auth_service):
        """Test error handling when getting user data"""
        # Configure mock to raise an exception
        mock_make_request.side_effect = Exception("API error")

        # Call get_user method and expect it to raise an exception
        with pytest.raises(Exception) as exc_info:
            auth_service.get_user(auth_token="invalid-token")

        # Verify the exception message
        assert "API error" in str(exc_info.value)

    @patch.object(SupabaseAuthService, "_make_request")
    def test_delete_user(self, mock_make_request, auth_service):
        """Test deleting a user as admin"""
        # Configure mock response
        mock_make_request.return_value = {}

        # Call delete_user method
        auth_service.delete_user(user_id="user-id")

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="DELETE", endpoint="/auth/v1/admin/users/user-id", is_admin=True
        )

    @patch.object(SupabaseAuthService, "_make_request")
    def test_list_users(self, mock_make_request, auth_service):
        """Test listing users as admin"""
        # Configure mock response
        mock_make_request.return_value = {
            "users": [
                {"id": "user-id-1", "email": "user1@example.com"},
                {"id": "user-id-2", "email": "user2@example.com"},
            ],
            "aud": "authenticated",
            "total": 2,
        }

        # Call list_users method
        result = auth_service.list_users()

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="GET", endpoint="/auth/v1/admin/users", is_admin=True
        )

        # Verify result
        assert len(result["users"]) == 2
        assert result["users"][0]["email"] == "user1@example.com"
        assert result["users"][1]["email"] == "user2@example.com"

    @patch.object(SupabaseAuthService, "_make_request")
    def test_invite_user_by_email(self, mock_make_request, auth_service):
        """Test inviting a user by email"""
        # Configure mock response
        mock_make_request.return_value = {
            "user": {
                "id": "user-id",
                "email": "test@example.com",
                "app_metadata": {},
                "user_metadata": {},
            }
        }

        # Call invite_user_by_email method
        result = auth_service.invite_user_by_email(
            email="test@example.com", user_metadata={"role": "editor"}
        )

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/auth/v1/invite",
            is_admin=True,
            data={"email": "test@example.com", "data": {"role": "editor"}},
        )

        # Verify result
        assert result["user"]["id"] == "user-id"
        assert result["user"]["email"] == "test@example.com"


class TestRealSupabaseAuthService:
    """Real-world integration tests for SupabaseAuthService
    
    These tests make actual API calls to Supabase and require:
    1. A valid Supabase URL and API keys in env variables
    2. Use of the --integration flag when running tests
    """
    
    @pytest.fixture
    def auth_service(self):
        """Create a real SupabaseAuthService instance"""
        return SupabaseAuthService()
    
    @pytest.fixture
    def test_email(self):
        """Generate a unique test email"""
        return f"test-{uuid.uuid4()}@example.com"
    
    @pytest.fixture
    def test_password(self):
        """Generate a test password"""
        return "Password123!"
    
    @pytest.mark.skipif(
        not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_ANON_KEY"),
        reason="Supabase credentials not set in environment variables",
    )
    def test_real_signup_and_signin(self, auth_service, test_email, test_password):
        """Test the actual signup and signin process with real Supabase"""
        # Skip if not using --integration flag
        if os.getenv("SKIP_INTEGRATION_TESTS", "true").lower() == "true":
            pytest.skip("Integration tests disabled")
        
        # Test creating a user
        try:
            user = auth_service.create_user(
                email=test_email,
                password=test_password,
                user_metadata={"full_name": "Test User"}
            )
            
            assert user is not None
            assert "id" in user
            assert user.get("email") == test_email
            
            # Test sign-in
            result = auth_service.sign_in_with_email(
                email=test_email,
                password=test_password
            )
            
            assert result is not None
            assert "access_token" in result
            assert "refresh_token" in result
            assert "user" in result
            assert result["user"]["email"] == test_email
            
            # Get user with token
            access_token = result["access_token"]
            user_data = auth_service.get_user(auth_token=access_token)
            
            assert user_data is not None
            assert user_data["email"] == test_email
            
            # Test sign-out
            sign_out_result = auth_service.sign_out(auth_token=access_token)
            assert sign_out_result is not None
            
        except Exception as e:
            pytest.fail(f"Real-world Supabase auth test failed: {str(e)}")
