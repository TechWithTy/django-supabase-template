import os
import random
import string
import logging
import pytest

from .. import _service as supabase_home_service
from ..auth import SupabaseAuthService
from ..init import get_supabase_client

logger = logging.getLogger(__name__)

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
    def supabase_client(self):
        """Get the Supabase client"""
        return get_supabase_client()
    
    @pytest.fixture
    def test_email(self):
        """Generate a random test email"""
        # Use a Gmail address format which is widely accepted
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"test.user.{random_suffix}@gmail.com"
    
    @pytest.fixture
    def test_password(self):
        """Generate a secure test password"""
        # Generate a password that meets common requirements
        password = ''.join(random.choices(string.ascii_letters, k=8))
        password += ''.join(random.choices(string.digits, k=2))
        password += random.choice('!@#$%^&*')
        return password
    
    @pytest.fixture
    def test_user_metadata(self):
        """Generate test user metadata"""
        return {
            "full_name": "Test User",
            "phone": "+1234567890",
            "custom_claim": "test-value"
        }
    
    def check_supabase_credentials(self):
        """Check if Supabase credentials are available"""
        if not os.getenv("SUPABASE_URL"):
            assert False, "SUPABASE_URL environment variable is not set"
        if not os.getenv("SUPABASE_ANON_KEY"):
            assert False, "SUPABASE_ANON_KEY environment variable is not set"
  
    
    def test_real_signup_and_signin(self, auth_service, test_email, test_password, test_user_metadata):
        """Test the actual signup and signin process with real Supabase"""
        self.check_supabase_credentials()

        try:
            # Test creating a user - no need to set is_admin as it's already set internally
            user = auth_service.create_user(
                email=test_email,
                password=test_password,
                user_metadata=test_user_metadata
            )

            assert user is not None
            assert "id" in user
            assert user.get("email") == test_email
            assert user.get("user_metadata", {}).get("full_name") == test_user_metadata["full_name"]

            # Try to sign in - using admin privileges to bypass email confirmation
            try:
                result = auth_service.sign_in_with_email(
                    email=test_email,
                    password=test_password,
                    is_admin=True
                )

                # If we get here, the sign-in worked (email confirmation might be disabled)
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
            except supabase_home_service.SupabaseAPIError as e:
                # Check if this is the expected email_not_confirmed error
                if e.details and e.details.get("error_code") == "email_not_confirmed":
                    # This is expected behavior when email confirmation is required
                    logger.info("Test skipped sign-in portion: email confirmation required")
                    pytest.skip("Email confirmation required - cannot test sign-in")
                else:
                    # Some other API error occurred
                    raise

        except Exception as e:
            pytest.fail(f"Real-world Supabase auth test failed: {str(e)}")

    def test_user_session_management(self, auth_service, test_email, test_password):
        """Test user session management including refresh tokens"""
        self.check_supabase_credentials()

        try:
            # Create a test user - no need to set is_admin as it's already set internally
            auth_service.create_user(
                email=test_email,
                password=test_password
            )

            # Try to sign in with admin privileges to bypass email confirmation
            try:
                # Sign in to get tokens
                auth_result = auth_service.sign_in_with_email(
                    email=test_email,
                    password=test_password,
                    is_admin=True
                )

                access_token = auth_result["access_token"]
                refresh_token = auth_result["refresh_token"]

                # Test getting session with token
                session = auth_service.get_session(auth_token=access_token)
                assert session is not None
                # The session structure might vary based on Supabase version
                # Check either session.user or session directly
                user_email = session.get("user", {}).get("email") or session.get("email")
                assert user_email == test_email

                # Test refreshing the session
                refresh_result = auth_service.refresh_session(refresh_token=refresh_token)
                assert refresh_result is not None
                assert "access_token" in refresh_result
                assert refresh_result["access_token"] != access_token  # Should be a new token

                # Test the new token works
                new_access_token = refresh_result["access_token"]
                new_session = auth_service.get_session(auth_token=new_access_token)
                assert new_session is not None
                # Check email in the appropriate location
                new_user_email = new_session.get("user", {}).get("email") or new_session.get("email")
                assert new_user_email == test_email

                # Clean up - sign out
                auth_service.sign_out(auth_token=new_access_token)
            except supabase_home_service.SupabaseAPIError as e:
                # Check if this is the expected email_not_confirmed error
                if e.details and e.details.get("error_code") == "email_not_confirmed":
                    # This is expected behavior when email confirmation is required
                    logger.info("Test skipped session management: email confirmation required")
                    pytest.skip("Email confirmation required - cannot test session management")
                else:
                    # Some other API error occurred
                    raise

        except Exception as e:
            pytest.fail(f"Session management test failed: {str(e)}")

    def test_password_reset_flow(self, auth_service, test_email, test_password, supabase_client):
        """Test password reset flow (without email verification)"""
        self.check_supabase_credentials()

        try:
            # Create a test user - no need to set is_admin as it's already set internally
            auth_service.create_user(
                email=test_email,
                password=test_password
            )

            # Some Supabase instances may have strict email validation
            # Let's use a more standard email format if needed
            try:
                reset_result = auth_service.reset_password(
                    email=test_email,
                    redirect_url="https://example.com/reset-password",
                    is_admin=True
                )
                assert reset_result is not None
            except supabase_home_service.SupabaseAPIError as e:
                if e.details and e.details.get("error_code") == "email_address_invalid":
                    # Try with a different email format or skip
                    logger.info(f"Email format '{test_email}' rejected by Supabase")
                    pytest.skip("Email format rejected by Supabase - cannot test password reset")
                elif e.details and e.details.get("error_code") == "email_not_confirmed":
                    # This is expected behavior when email confirmation is required
                    logger.info("Test skipped password reset: email confirmation required")
                    pytest.skip("Email confirmation required - cannot test password reset")
                else:
                    # Some other API error occurred
                    raise

            # Note: We can't fully test the reset flow as it requires clicking an email link
            # But we can verify the API accepts the request

            # Clean up - we can use admin functions to delete the user if service key is available
            if os.getenv("SUPABASE_SERVICE_KEY"):
                user_id = auth_service.get_user_by_email(email=test_email)["id"]
                auth_service.delete_user(user_id=user_id)

        except Exception as e:
            pytest.fail(f"Password reset test failed: {str(e)}")

    def test_user_management_admin(self, auth_service, test_email, test_password, test_user_metadata):
        """Test admin user management functions"""
        self.check_supabase_credentials()
        
        # Check if service role key is available - but make this a conditional test
        # instead of failing outright
        if not os.getenv("SUPABASE_SERVICE_KEY"):
            pytest.skip("SUPABASE_SERVICE_KEY not set, skipping admin tests")
            return
        
        try:
            # Create a user with admin API
            user = auth_service.create_user(
                email=test_email,
                password=test_password,
                user_metadata=test_user_metadata
            )
            
            user_id = user["id"]
            
            # Get user by ID
            user_by_id = auth_service.get_user_by_id(user_id=user_id)
            assert user_by_id is not None
            assert user_by_id["id"] == user_id
            
            # Get user by email
            user_by_email = auth_service.get_user_by_email(email=test_email)
            assert user_by_email is not None
            assert user_by_email["email"] == test_email
            
            # Update user metadata
            updated_metadata = {"full_name": "Updated Name", "role": "tester"}
            update_result = auth_service.update_user_metadata(
                user_id=user_id,
                user_metadata=updated_metadata
            )
            
            assert update_result is not None
            assert update_result["user_metadata"]["full_name"] == "Updated Name"
            
            # Delete the user
            delete_result = auth_service.delete_user(user_id=user_id)
            assert delete_result is not None
            
            # Verify user is deleted
            try:
                auth_service.get_user_by_id(user_id=user_id)
                pytest.fail("User should be deleted but was found")
            except Exception:
                # Expected exception when user is not found
                pass
            
        except Exception as e:
            pytest.fail(f"Admin user management test failed: {str(e)}")
    
    def test_anonymous_user(self, auth_service):
        """Test creating and using anonymous users"""
        self.check_supabase_credentials()
        
        try:
            # Create an anonymous user
            anon_result = auth_service.create_anonymous_user()
            
            assert anon_result is not None
            assert "access_token" in anon_result
            assert "refresh_token" in anon_result
            assert "user" in anon_result
            assert anon_result["user"]["aud"] == "authenticated"
            
            # Check is_anonymous if it exists, but don't fail if it doesn't
            # Some Supabase versions may not have this field
            if "is_anonymous" in anon_result["user"]:
                assert anon_result["user"]["is_anonymous"]
            
            # Get the session with the token
            access_token = anon_result["access_token"]
            session = auth_service.get_session(auth_token=access_token)
            
            assert session is not None
            
            # The session structure might vary based on Supabase version
            # Don't assume user key exists, check the structure first
            if "user" in session and "is_anonymous" in session["user"]:
                assert session["user"]["is_anonymous"]
            
            # Sign out
            auth_service.sign_out(auth_token=access_token)
            
        except Exception as e:
            pytest.fail(f"Anonymous user test failed: {str(e)}")
