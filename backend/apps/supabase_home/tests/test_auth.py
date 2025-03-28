import pytest
import os
import uuid
from unittest.mock import patch

from ..auth import SupabaseAuthService


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
