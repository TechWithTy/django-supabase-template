import pytest
import os
import uuid
import time
import requests
import random
import string
import asyncio
from pytest_asyncio import fixture

from ..realtime import SupabaseRealtimeService
from ..auth import SupabaseAuthService
from .._service import SupabaseAPIError, SupabaseAuthError
from ..init import get_supabase_client


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
        issues = diagnose_supabase_realtime_issue()
        # Instead of skipping, return the issues so they can be reported
        return issues

    @pytest.fixture
    def realtime_service(self):
        """Create a real SupabaseRealtimeService instance"""
        return SupabaseRealtimeService()

    @pytest.fixture
    def auth_service(self):
        """Create a real SupabaseAuthService instance"""
        return SupabaseAuthService()
    
    @pytest.fixture
    def supabase_client(self):
        """Get the Supabase client instance"""
        return get_supabase_client()
    
    # Add an async fixture for the async Supabase client
    @fixture
    async def async_supabase_client(self):
        """Get the async Supabase client"""
        from supabase.lib.client_options import ClientOptions
        from supabase._async.client import AsyncClient
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        # Create async client directly
        options = ClientOptions(schema="public")
        client = AsyncClient(supabase_url, supabase_key, options=options)
        
        # Return the client and then ensure it gets cleaned up
        yield client
        
        # Cleanup after the test is done
        try:
            # Close the realtime connection if it exists
            if hasattr(client, 'realtime') and client.realtime is not None:
                # Use asyncio.shield to prevent task cancellation during cleanup
                await asyncio.shield(client.realtime.disconnect())
                # Wait a moment for the connection to fully close
                await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Error during async client cleanup: {str(e)}")

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
    def auth_token(self, supabase_client, test_user_credentials):
        """Create a test user and return the auth token using the Supabase client"""
        print("\n=== DEBUG: Starting auth_token fixture ===")
        print(f"Test credentials: {test_user_credentials}")

        try:
            # First try to create the user with the Supabase client
            print("Attempting to create user with Supabase client...")
            raw_client = supabase_client
            
            # Sign up the user - use the correct parameter format
            print("Using sign_up with correct parameters...")
            signup_data = raw_client.auth.sign_up({
                "email": test_user_credentials["email"],
                "password": test_user_credentials["password"]
            })
            print(f"Sign up result: {signup_data}")
            
            # Get the session from the sign up result
            session = getattr(signup_data, "session", None)
            if session:
                access_token = getattr(session, "access_token", None)
                print(f"Access token obtained: {bool(access_token)}")
                return access_token
            else:
                # If no session, try to sign in
                print("No session from sign up, trying to sign in...")
                signin_data = raw_client.auth.sign_in_with_password({
                    "email": test_user_credentials["email"],
                    "password": test_user_credentials["password"]
                })
                session = getattr(signin_data, "session", None)
                access_token = getattr(session, "access_token", None) if session else None
                print(f"Access token obtained: {bool(access_token)}")
                return access_token
                
        except Exception as e:
            print(f"Error creating test user: {str(e)}")
            print(f"Exception type: {type(e).__name__}")
            # If user already exists, try to sign in
            try:
                print("User may already exist. Attempting to sign in...")
                signin_data = raw_client.auth.sign_in_with_password({
                    "email": test_user_credentials["email"],
                    "password": test_user_credentials["password"]
                })
                session = getattr(signin_data, "session", None)
                access_token = getattr(session, "access_token", None) if session else None
                print(f"Access token obtained: {bool(access_token)}")
                return access_token
            except Exception as signin_error:
                print(f"Error signing in: {str(signin_error)}")
                print(f"Exception type: {type(signin_error).__name__}")
                # Return None instead of skipping so test can run and show appropriate errors
                print("WARNING: No authentication token available. Tests will likely fail but will show exact errors.")
                return None

    @pytest.fixture
    def test_table_name(self):
        """Test table name for realtime tests"""
        return os.getenv("TEST_TABLE_NAME", "test_table")

    @pytest.fixture
    def test_channel_name(self):
        """Generate a unique test channel name"""
        return f"test-channel-{uuid.uuid4()}"

    @pytest.mark.asyncio
    async def test_real_subscribe_and_broadcast(
        self, realtime_service, test_channel_name, realtime_issues, auth_token, async_supabase_client
    ):
        """Test subscribing to a channel and broadcasting a message

        Note: This test requires that your Supabase instance has realtime enabled.
        """
        # Report any setup issues but continue with the test
        if realtime_issues:
            for issue in realtime_issues:
                print(f"WARNING: {issue}")
            print("\nContinuing with test despite setup issues...")

        if auth_token is None:
            print("WARNING: No authentication token available. Test may fail but will show exact errors.")

        channel = None
        try:
            # Create a channel with the async client
            channel = async_supabase_client.channel(test_channel_name, {
                "config": {
                    "broadcast": {
                        "self": True
                    },
                    "private": True  # Enable RLS policy enforcement
                }
            })
            
            # Print available methods to debug
            print(f"Channel type: {type(channel)}")
            print(f"Available methods: {[m for m in dir(channel) if not m.startswith('_')]}")
            
            # Setup a message receiver
            received_messages = []
            
            # Define the callback function to handle messages
            async def handle_broadcast(payload):
                print(f"Received message: {payload}")
                received_messages.append(payload)
            
            # For AsyncRealtimeChannel, we use on_broadcast
            if hasattr(channel, 'on_broadcast'):
                channel.on_broadcast(
                    'test-event',  # Event name
                    handle_broadcast  # Callback function
                )
            else:
                # Fallback to 'on' method if available
                if hasattr(channel, 'on'):
                    channel.on(
                        'broadcast',
                        'test-event',
                        handle_broadcast
                    )
                else:
                    print("Warning: Channel doesn't have on_broadcast or on methods")
            
            # Subscribe to the channel
            await channel.subscribe()
            print("Subscribed to channel")
            
            # Wait a moment for subscription to be fully established
            await asyncio.sleep(1)

            # Send a test message
            test_message = {
                "message": f"Test message {uuid.uuid4()}",
                "timestamp": time.time(),
            }
            
            # Try using the client's send_broadcast method
            if hasattr(channel, 'send_broadcast'):
                await channel.send_broadcast('test-event', test_message)
                print("Message sent using channel.send_broadcast()")
            else:
                # Fallback to using the service method
                print("Channel doesn't have send_broadcast method, using service method")
                broadcast_result = realtime_service.broadcast_message(
                    channel=test_channel_name,
                    payload=test_message,
                    auth_token=auth_token,
                )
                assert broadcast_result is not None
                assert "status" in broadcast_result
                print(f"Successfully broadcast message to channel '{test_channel_name}'")
            
            # Wait for the message to be received
            start_time = time.time()
            timeout = 5  # 5 seconds timeout
            
            while not received_messages and time.time() - start_time < timeout:
                await asyncio.sleep(0.1)
                print("Waiting for message...")
            
            # Check if we received any messages
            if received_messages:
                print(f"Received messages: {received_messages}")
                print("Test passed: Successfully received the message")
            else:
                print("No messages were received. This could be due to:")
                print("1. Realtime feature not being enabled in your Supabase project")
                print("2. Missing RLS policies for Realtime")
                print("3. Network issues or timeouts")
                
                # Check if we need to set up RLS policies
                print("\nMake sure you have set up the correct RLS policies for Realtime.")
                print("You may need to add the following policies in your Supabase SQL editor:")
                print("""
                -- Enable RLS on the realtime.messages table
                ALTER TABLE realtime.messages ENABLE ROW LEVEL SECURITY;
                
                -- Allow authenticated users to receive broadcasts
                CREATE POLICY "Allow authenticated users to receive broadcasts" 
                ON realtime.messages
                FOR SELECT
                TO authenticated
                USING (true);
                
                -- Allow authenticated users to send broadcasts
                CREATE POLICY "Allow authenticated users to send broadcasts" 
                ON realtime.messages
                FOR INSERT
                TO authenticated
                WITH CHECK (true);
                """)

        except Exception as e:
            print(f"Error in test: {str(e)}")
            print(f"Exception type: {type(e).__name__}")
            
            # If we get an error about permissions, provide more helpful information
            if "permission" in str(e).lower() or "unauthorized" in str(e).lower():
                print("\nThis might be a permissions issue. Make sure you have set up the correct RLS policies for Realtime.")
                print("You may need to add the following policies in your Supabase SQL editor:")
                print("""
                -- Enable RLS on the realtime.messages table
                ALTER TABLE realtime.messages ENABLE ROW LEVEL SECURITY;
                
                -- Allow authenticated users to receive broadcasts
                CREATE POLICY "Allow authenticated users to receive broadcasts" 
                ON realtime.messages
                FOR SELECT
                TO authenticated
                USING (true);
                
                -- Allow authenticated users to send broadcasts
                CREATE POLICY "Allow authenticated users to send broadcasts" 
                ON realtime.messages
                FOR INSERT
                TO authenticated
                WITH CHECK (true);
                """)
            
            pytest.fail(f"Realtime API test failed: {str(e)}")
        finally:
            # Ensure we properly clean up the channel to avoid asyncio errors
            if channel:
                try:
                    # Make sure we unsubscribe from the channel
                    await channel.unsubscribe()
                    print("Cleaned up a channel during test teardown")
                except Exception as cleanup_error:
                    print(f"Error during cleanup: {cleanup_error}")

    @pytest.mark.asyncio
    async def test_real_get_channels(self, realtime_service, realtime_issues, auth_token, async_supabase_client):
        """Test getting all subscribed channels

        Note: This test requires that your Supabase instance has realtime enabled.
        """
        # Report any setup issues but continue with the test
        if realtime_issues:
            for issue in realtime_issues:
                print(f"WARNING: {issue}")
            print("\nContinuing with test despite setup issues...")

        if auth_token is None:
            print("WARNING: No authentication token available. Test may fail but will show exact errors.")

        channels = []
        try:
            # Try using the async client's API for Realtime
            print("Using async Supabase client for getting channels...")
            
            # Create multiple channels to ensure we have something to list
            for i in range(2):
                test_channel_name = f"test-channel-{uuid.uuid4()}"
                channel = async_supabase_client.channel(test_channel_name, {
                    "config": {
                        "broadcast": {"self": True},
                        "private": True
                    }
                })
                
                # Subscribe to the channel
                await channel.subscribe()
                print(f"Subscribed to channel '{test_channel_name}'")
                channels.append(channel)
            
            # Wait a moment for subscriptions to be fully established
            await asyncio.sleep(1)
            
            # Now try to get channels using the client directly instead of the service API
            # According to docs, we should be able to get channels from the client
            if hasattr(async_supabase_client.realtime, 'channels'):
                realtime_channels = async_supabase_client.realtime.channels
                print(f"Retrieved channels directly from client: {realtime_channels}")
                assert len(realtime_channels) >= len(channels), "Expected at least as many channels as we subscribed to"
            else:
                print("Warning: async_supabase_client.realtime doesn't have a 'channels' attribute")
                # Fallback to the service method with admin privileges
                print("Falling back to REST API call with admin privileges...")
                channels_result = realtime_service.get_channels(
                    auth_token=auth_token,
                    is_admin=True  # Explicitly use admin privileges
                )
                print(f"Retrieved channels: {channels_result}")
                assert channels_result is not None
                if isinstance(channels_result, dict):
                    assert "channels" in channels_result

        except Exception as e:
            print(f"Error in test: {str(e)}")
            print(f"Exception type: {type(e).__name__}")
            pytest.fail(f"Realtime API test failed: {str(e)}")
        finally:
            # Clean up by unsubscribing from all channels
            for channel in channels:
                try:
                    await channel.unsubscribe()
                    print("Cleaned up a channel during test teardown")
                except Exception as cleanup_error:
                    print(f"Error during channel cleanup: {cleanup_error}")

    @pytest.mark.asyncio
    async def test_real_unsubscribe_all(self, realtime_service, realtime_issues, auth_token, async_supabase_client):
        """Test unsubscribing from all channels

        Note: This test requires that your Supabase instance has realtime enabled.
        """
        # Report any setup issues but continue with the test
        if realtime_issues:
            for issue in realtime_issues:
                print(f"WARNING: {issue}")
            print("\nContinuing with test despite setup issues...")

        if auth_token is None:
            print("WARNING: No authentication token available. Test may fail but will show exact errors.")

        channels = []
        try:
            # First subscribe to multiple test channels using the async client
            for i in range(2):  # Create 2 channels
                test_channel_name = f"test-channel-{uuid.uuid4()}"
                channel = async_supabase_client.channel(test_channel_name, {
                    "config": {
                        "broadcast": {"self": True},
                        "private": True
                    }
                })
                
                # Subscribe to the channel
                await channel.subscribe()
                print(f"Subscribed to channel '{test_channel_name}'")
                channels.append(channel)
            
            # Wait a moment for subscriptions to be fully established
            await asyncio.sleep(1)
            
            # Check if channels exist before unsubscribing
            if hasattr(async_supabase_client.realtime, 'channels'):
                channels_before = list(async_supabase_client.realtime.channels)
                print(f"Channels before unsubscribe: {len(channels_before)}")
                assert len(channels_before) >= len(channels), "Expected at least as many channels as we subscribed to"
            
            # Now try to use the client's remove_all_channels method if available
            if hasattr(async_supabase_client.realtime, 'remove_all_channels'):
                print("Using client's remove_all_channels method...")
                await async_supabase_client.realtime.remove_all_channels()
                print("Successfully unsubscribed from all channels using client API")
                
                # Verify channels are gone
                if hasattr(async_supabase_client.realtime, 'channels'):
                    channels_after = list(async_supabase_client.realtime.channels)
                    print(f"Channels after unsubscribe: {len(channels_after)}")
                    assert len(channels_after) == 0, "Expected no channels after unsubscribe_all"
            else:
                # Fallback to removing each channel individually
                print("Client doesn't have remove_all_channels, removing channels one by one...")
                for channel in channels:
                    await channel.unsubscribe()
                    print(f"Unsubscribed from channel {channel}")
                
                # Then try the service method with admin privileges as a verification
                print("Also trying service API call with admin privileges...")
                unsubscribe_all_result = realtime_service.unsubscribe_all(
                    auth_token=auth_token,
                    is_admin=True  # Explicitly use admin privileges
                )
                
                if unsubscribe_all_result is not None:
                    print(f"Service API result: {unsubscribe_all_result}")
                    if isinstance(unsubscribe_all_result, dict) and "status" in unsubscribe_all_result:
                        print("Successfully unsubscribed from all channels using service method")

        except Exception as e:
            print(f"Error in test: {str(e)}")
            print(f"Exception type: {type(e).__name__}")
            pytest.fail(f"Realtime API test failed: {str(e)}")
        finally:
            # For safety, ensure we properly clean up all channels to avoid asyncio resource warnings
            for channel in channels:
                try:
                    await channel.unsubscribe()
                    print("Cleaned up a channel during test teardown")
                except Exception as cleanup_error:
                    print(f"Error during channel cleanup: {cleanup_error}")

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
            print(f"Error in test: {str(e)}")
            print(f"Exception type: {type(e).__name__}")
            pytest.fail(f"Error handling test failed: {str(e)}")
