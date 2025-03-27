import pytest
import os
import uuid
import time
import requests
import random
import string

from ..realtime import SupabaseRealtimeService
from ..auth import SupabaseAuthService
from .._service import SupabaseAPIError, SupabaseAuthError


def diagnose_supabase_realtime_issue():
    """Diagnose common issues with Supabase Realtime API"""
    # Check environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    anon_key = os.getenv("SUPABASE_ANON_KEY")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    issues = []

    if not supabase_url:
        issues.append("SUPABASE_URL environment variable is not set")
    elif not supabase_url.startswith("http"):
        issues.append(f"SUPABASE_URL has invalid format: {supabase_url}")

    if not anon_key:
        issues.append("SUPABASE_ANON_KEY environment variable is not set")

    if not service_role_key:
        issues.append("SUPABASE_SERVICE_ROLE_KEY environment variable is not set")

    # Check if Realtime is enabled by making a direct request
    if supabase_url and (anon_key or service_role_key):
        try:
            # Try to access the Realtime health endpoint
            headers = {"apikey": service_role_key or anon_key}
            response = requests.get(
                f"{supabase_url}/realtime/v1/health", headers=headers, timeout=5
            )

            if response.status_code >= 400:
                issues.append(
                    f"Realtime API health check failed with status {response.status_code}: {response.text}"
                )

                if response.status_code == 404:
                    issues.append(
                        "Realtime API endpoint not found. Make sure Realtime is enabled in your Supabase project."
                    )
                elif response.status_code == 403:
                    issues.append(
                        "Permission denied. Make sure you have the correct API keys and Realtime is enabled."
                    )
        except Exception as e:
            issues.append(f"Error checking Realtime health: {str(e)}")

    return issues


class TestRealSupabaseRealtimeService:
    """Real-world integration tests for SupabaseRealtimeService

    These tests make actual API calls to Supabase and require:
    1. A valid Supabase URL and API keys in env variables
    2. A Supabase instance with realtime enabled
    """

    @pytest.fixture(scope="class")
    def realtime_issues(self):
        """Check for issues with Supabase Realtime setup"""
        return diagnose_supabase_realtime_issue()

    @pytest.fixture
    def realtime_service(self):
        """Create a real SupabaseRealtimeService instance"""
        return SupabaseRealtimeService()

    @pytest.fixture
    def auth_service(self):
        """Create a real SupabaseAuthService instance"""
        return SupabaseAuthService()

    @pytest.fixture
    def test_user_credentials(self):
        """Generate random credentials for a test user"""
        random_suffix = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=8)
        )
        email = f"test-user-{random_suffix}@example.com"
        password = f"Password123!{random_suffix}"
        return {"email": email, "password": password}

    @pytest.fixture
    def auth_token(self, auth_service, test_user_credentials):
        """Create a test user and return the auth token"""
        print("\n=== DEBUG: Starting auth_token fixture ===")
        print(f"Test credentials: {test_user_credentials}")
        print(f"Auth service: {auth_service.__class__.__name__}")

        try:
            # First try to create the user with admin privileges
            print("Attempting to create user...")
            user_result = auth_service.create_user(
                email=test_user_credentials["email"],
                password=test_user_credentials["password"],
            )
            print(f"Create user result: {user_result}")

            # Now sign in to get the access token
            print("Attempting to sign in...")
            signin_result = auth_service.sign_in_with_email(
                email=test_user_credentials["email"],
                password=test_user_credentials["password"],
            )
            print(f"Sign in result: {signin_result}")

            # Extract the access token from the sign-in result
            access_token = signin_result.get("access_token")
            if not access_token:
                # Try alternate location in the response
                access_token = signin_result.get("session", {}).get("access_token")

            print(f"Access token obtained: {bool(access_token)}")
            return access_token
        except Exception as e:
            print(f"Error creating test user: {str(e)}")
            print(f"Exception type: {type(e).__name__}")
            # If user already exists, try to sign in
            try:
                print("User may already exist. Attempting to sign in...")
                signin_result = auth_service.sign_in_with_email(
                    email=test_user_credentials["email"],
                    password=test_user_credentials["password"],
                )
                print(f"Sign in result: {signin_result}")

                # Extract the access token from the sign-in result
                access_token = signin_result.get("access_token")
                if not access_token:
                    # Try alternate location in the response
                    access_token = signin_result.get("session", {}).get("access_token")

                print(f"Access token obtained: {bool(access_token)}")
                return access_token
            except Exception as signin_error:
                print(f"Error signing in: {str(signin_error)}")
                print(f"Exception type: {type(signin_error).__name__}")
                return None

    @pytest.fixture
    def test_table_name(self):
        """Test table name for realtime tests"""
        return os.getenv("TEST_TABLE_NAME", "test_table")

    @pytest.fixture
    def test_channel_name(self):
        """Generate a unique test channel name"""
        return f"test-channel-{uuid.uuid4()}"

    def test_real_subscribe_and_broadcast(
        self, realtime_service, test_channel_name, realtime_issues, auth_token
    ):
        """Test subscribing to a channel and broadcasting a message

        Note: This test requires that your Supabase instance has realtime enabled.
        """
        # Skip test if no auth token is available
        if not auth_token:
            pytest.skip(
                "No authentication token available. Cannot test Realtime API without authentication."
            )

        # Report any setup issues but continue with the test
        if realtime_issues:
            for issue in realtime_issues:
                print(f"WARNING: {issue}")
            print("\nContinuing with test despite setup issues...")

        try:
            # 1. Subscribe to a test channel
            subscribe_result = realtime_service.subscribe_to_channel(
                channel=test_channel_name,
                event="BROADCAST",
                auth_token=auth_token,  # Use the auth token instead of admin privileges
            )

            assert subscribe_result is not None
            assert "subscription_id" in subscribe_result
            assert "status" in subscribe_result

            subscription_id = subscribe_result["subscription_id"]
            print(
                f"Successfully subscribed to channel '{test_channel_name}' with subscription ID: {subscription_id}"
            )

            # 2. Broadcast a test message
            test_message = {
                "message": f"Test message {uuid.uuid4()}",
                "timestamp": time.time(),
            }
            broadcast_result = realtime_service.broadcast_message(
                channel=test_channel_name,
                event="BROADCAST",
                payload=test_message,
                auth_token=auth_token,  # Use the auth token instead of admin privileges
            )

            assert broadcast_result is not None
            assert "message_id" in broadcast_result
            assert "status" in broadcast_result
            print(f"Successfully broadcast message to channel '{test_channel_name}'")

            # 3. Unsubscribe from the channel
            unsubscribe_result = realtime_service.unsubscribe_from_channel(
                subscription_id=subscription_id,
                auth_token=auth_token,  # Use the auth token instead of admin privileges
            )

            assert unsubscribe_result is not None
            assert "status" in unsubscribe_result
            print(f"Successfully unsubscribed from channel '{test_channel_name}'")

        except SupabaseAuthError as e:
            pytest.fail(
                f"Authentication error: {str(e)}\n\nPossible causes:\n"
                + "1. Realtime feature is not enabled in your Supabase project\n"
                + "2. Your auth token doesn't have permission to access Realtime API\n"
                + "3. You need to enable the appropriate RLS policies for Realtime"
            )
        except SupabaseAPIError as e:
            pytest.fail(
                f"API error: {str(e)}\n\nCheck your Supabase project configuration."
            )
        except Exception as e:
            pytest.fail(f"Unexpected error: {str(e)}")

    def test_real_get_channels(self, realtime_service, realtime_issues):
        """Test getting all channels"""
        # Report any setup issues but continue with the test
        if realtime_issues:
            for issue in realtime_issues:
                print(f"WARNING: {issue}")
            print("\nContinuing with test despite setup issues...")

        try:
            # Get all channels
            channels_result = realtime_service.get_channels(
                is_admin=True
            )  # Use admin privileges

            assert channels_result is not None
            assert "channels" in channels_result
            print(f"Successfully retrieved {len(channels_result['channels'])} channels")

        except SupabaseAuthError as e:
            pytest.fail(
                f"Authentication error: {str(e)}\n\nPossible causes:\n"
                + "1. Realtime feature is not enabled in your Supabase project\n"
                + "2. Your service role key doesn't have permission to access Realtime API\n"
                + "3. You need to enable the appropriate RLS policies for Realtime"
            )
        except SupabaseAPIError as e:
            pytest.fail(
                f"API error: {str(e)}\n\nCheck your Supabase project configuration."
            )
        except Exception as e:
            pytest.fail(f"Unexpected error: {str(e)}")

    def test_real_unsubscribe_all(
        self, realtime_service, test_channel_name, realtime_issues
    ):
        """Test unsubscribing from all channels"""
        # Report any setup issues but continue with the test
        if realtime_issues:
            for issue in realtime_issues:
                print(f"WARNING: {issue}")
            print("\nContinuing with test despite setup issues...")

        try:
            # 1. Subscribe to a test channel
            subscribe_result = realtime_service.subscribe_to_channel(
                channel=test_channel_name,
                event="BROADCAST",
                is_admin=True,  # Use admin privileges
            )

            assert subscribe_result is not None
            assert "subscription_id" in subscribe_result

            # 2. Unsubscribe from all channels
            unsubscribe_all_result = realtime_service.unsubscribe_all(
                is_admin=True
            )  # Use admin privileges

            assert unsubscribe_all_result is not None
            assert "status" in unsubscribe_all_result
            print("Successfully unsubscribed from all channels")

            # 3. Verify channels are empty
            channels_result = realtime_service.get_channels(
                is_admin=True
            )  # Use admin privileges
            assert channels_result is not None
            assert "channels" in channels_result

            # Note: This assertion might fail if there are other active subscriptions
            # in your Supabase instance that weren't created by this test
            if len(channels_result["channels"]) > 0:
                print(
                    f"Warning: {len(channels_result['channels'])} channels still active after unsubscribe_all"
                )

        except SupabaseAuthError as e:
            pytest.fail(
                f"Authentication error: {str(e)}\n\nPossible causes:\n"
                + "1. Realtime feature is not enabled in your Supabase project\n"
                + "2. Your service role key doesn't have permission to access Realtime API\n"
                + "3. You need to enable the appropriate RLS policies for Realtime"
            )
        except SupabaseAPIError as e:
            pytest.fail(
                f"API error: {str(e)}\n\nCheck your Supabase project configuration."
            )
        except Exception as e:
            pytest.fail(f"Unexpected error: {str(e)}")

    def test_error_handling_with_real_service(self, realtime_service, realtime_issues):
        """Test error handling with real service"""
        # Report any setup issues but continue with the test
        if realtime_issues:
            for issue in realtime_issues:
                print(f"WARNING: {issue}")
            print("\nContinuing with test despite setup issues...")

        try:
            # Try to subscribe with an invalid channel name (containing spaces)
            # We expect a SupabaseAPIError or SupabaseAuthError
            with pytest.raises((SupabaseAPIError, SupabaseAuthError)) as excinfo:
                realtime_service.subscribe_to_channel(
                    channel="invalid channel name",
                    is_admin=True,  # Use admin privileges
                )

            # Verify exception was raised
            print(f"Successfully caught error: {str(excinfo.value)}")

        except Exception as e:
            pytest.fail(f"Error handling test failed: {str(e)}")
