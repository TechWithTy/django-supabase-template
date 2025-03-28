import pytest
import os
import uuid
import time
import random
import string
import asyncio
from pytest_asyncio import fixture

from ..init import get_supabase_client


def diagnose_supabase_realtime_issue():
    """Diagnose common issues with Supabase Realtime API"""
    issues = []
    
    # Check if environment variables are set
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url:
        issues.append("SUPABASE_URL environment variable is not set")
    if not supabase_key:
        issues.append("SUPABASE_ANON_KEY environment variable is not set")
    
    if issues:
        return issues
    
    # Check if Realtime API is accessible
    try:
        # Initialize the Supabase client
        get_supabase_client()  # Just check if we can initialize the client
        
        # Check if we can connect to Supabase
        print(f"Checking Supabase connection to {supabase_url}...")
        
        # We'll consider the connection successful if we can initialize the client
        print("Supabase client initialized successfully")
        
        return issues
    except Exception as e:
        issues.append(f"Error connecting to Supabase: {str(e)}")
        return issues



class TestSupabaseRealtime:
    """Tests for Supabase Realtime using the official client
    
    These tests make actual API calls to Supabase and require:
    1. A valid Supabase URL and API key in env variables
    2. A Supabase instance with realtime enabled
    3. Proper RLS policies configured for Realtime
    """
    
    @pytest.fixture(scope="class")
    def realtime_issues(self):
        """Check for issues with Supabase Realtime setup"""
        return diagnose_supabase_realtime_issue()
    
    @pytest.fixture
    def supabase_client(self):
        """Get the Supabase client"""
        return get_supabase_client()
    
    @pytest.fixture
    def test_user_credentials(self):
        """Generate random credentials for a test user"""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        email = f"test-user-{random_suffix}@example.com"
        password = f"Password123!{random_suffix}"
        return {"email": email, "password": password}
    
    @pytest.fixture
    def auth_token(self, supabase_client, test_user_credentials):
        """Create a test user and return the auth tokens"""
        print("\n=== DEBUG: Starting auth_token fixture ===")
        print(f"Test credentials: {test_user_credentials}")
        
        try:
            # Sign up a new user
            print("Attempting to sign up user...")
            signup_result = supabase_client.auth.sign_up({
                "email": test_user_credentials["email"],
                "password": test_user_credentials["password"]
            })
            print(f"Sign up result: {signup_result}")
            
            # Extract the session tokens
            session = signup_result.session
            if session:
                access_token = session.access_token
                refresh_token = session.refresh_token
                print(f"Access token obtained from signup: {bool(access_token)}")
                return {"access_token": access_token, "refresh_token": refresh_token}
            else:
                print("No session in signup result, trying sign in...")
                
                # Try to sign in
                signin_result = supabase_client.auth.sign_in_with_password({
                    "email": test_user_credentials["email"],
                    "password": test_user_credentials["password"]
                })
                
                if signin_result.session:
                    access_token = signin_result.session.access_token
                    refresh_token = signin_result.session.refresh_token
                    print(f"Access token obtained from signin: {bool(access_token)}")
                    return {"access_token": access_token, "refresh_token": refresh_token}
                else:
                    print("No session in signin result")
                    return None
                
        except Exception as e:
            print(f"Error in signup: {str(e)}")
            print(f"Exception type: {type(e).__name__}")
            
            # Try to sign in if user might already exist
            try:
                print("User may already exist. Attempting to sign in...")
                signin_result = supabase_client.auth.sign_in_with_password({
                    "email": test_user_credentials["email"],
                    "password": test_user_credentials["password"]
                })
                
                if signin_result.session:
                    access_token = signin_result.session.access_token
                    refresh_token = signin_result.session.refresh_token
                    print(f"Access token obtained from signin: {bool(access_token)}")
                    return {"access_token": access_token, "refresh_token": refresh_token}
                else:
                    print("No session in signin result")
                    return None
                    
            except Exception as signin_error:
                print(f"Error signing in: {str(signin_error)}")
                print(f"Exception type: {type(signin_error).__name__}")
                return None
    
    @pytest.fixture
    def test_channel_name(self):
        """Generate a unique test channel name"""
        return f"test-channel-{uuid.uuid4()}"
    
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
        return AsyncClient(supabase_url, supabase_key, options=options)
    
    # Add an async fixture for auth token
    @fixture
    async def async_auth_token(self, async_supabase_client, test_user_credentials):
        """Create a test user and return the auth tokens using the async client"""
        print("\n=== DEBUG: Starting async_auth_token fixture ===")
        print(f"Test credentials: {test_user_credentials}")
        
        try:
            # Sign up a new user
            print("Attempting to sign up user with async client...")
            # Use the sync client as a fallback since we're having issues with the async methods
            from ..init import get_supabase_client
            sync_client = get_supabase_client()
            
            signup_result = sync_client.auth.sign_up({
                "email": test_user_credentials["email"],
                "password": test_user_credentials["password"]
            })
            print(f"Sync sign up result: {signup_result}")
            
            # Extract the session tokens
            session = signup_result.session
            if session:
                access_token = session.access_token
                refresh_token = session.refresh_token
                print(f"Access token obtained from sync signup: {bool(access_token)}")
                return {"access_token": access_token, "refresh_token": refresh_token}
            else:
                print("No session in sync signup result, trying sign in...")
                
                # Try to sign in
                signin_result = sync_client.auth.sign_in_with_password({
                    "email": test_user_credentials["email"],
                    "password": test_user_credentials["password"]
                })
                
                if signin_result.session:
                    access_token = signin_result.session.access_token
                    refresh_token = signin_result.session.refresh_token
                    print(f"Access token obtained from sync signin: {bool(access_token)}")
                    return {"access_token": access_token, "refresh_token": refresh_token}
                else:
                    print("No session in sync signin result")
                    return None
                
        except Exception as e:
            print(f"Error in sync signup: {str(e)}")
            print(f"Exception type: {type(e).__name__}")
            
            # Try to sign in if user might already exist
            try:
                print("User may already exist. Attempting to sign in with sync client...")
                from ..init import get_supabase_client
                sync_client = get_supabase_client()
                
                signin_result = sync_client.auth.sign_in_with_password({
                    "email": test_user_credentials["email"],
                    "password": test_user_credentials["password"]
                })
                
                if signin_result.session:
                    access_token = signin_result.session.access_token
                    refresh_token = signin_result.session.refresh_token
                    print(f"Access token obtained from sync signin: {bool(access_token)}")
                    return {"access_token": access_token, "refresh_token": refresh_token}
                else:
                    print("No session in sync signin result")
                    return None
                    
            except Exception as signin_error:
                print(f"Error signing in with sync client: {str(signin_error)}")
                print(f"Exception type: {type(signin_error).__name__}")
                return None
    
    # Convert the test to use a hybrid approach - use the sync client for authentication and the async client only for Realtime functionality
    @pytest.mark.asyncio
    async def test_async_realtime_subscribe_and_broadcast(self, async_supabase_client, test_channel_name, realtime_issues, async_auth_token):
        """Test subscribing to a channel and broadcasting a message using the async client"""
        # Instead of skipping, print a warning and continue to see actual errors
        if async_auth_token is None:
            print("WARNING: No auth token available. Test will likely fail but will show exact errors.")

        # Report any setup issues but continue with the test
        if realtime_issues:
            for issue in realtime_issues:
                print(f"WARNING: {issue}")
            print("\nContinuing with test despite setup issues...")
        
        channel = None
        try:
            # Create a channel with the async client
            # For authenticated channels, use the 'private' option
            channel = async_supabase_client.channel(test_channel_name, {
                "config": {
                    "broadcast": {
                        "self": True
                    }
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
            
            # Define the subscription callback
            async def on_subscribe(status, err=None):
                print(f"Subscription status: {status}")
                print(f"Subscription error: {err}")
                
                # Only send message if successfully subscribed
                if status == "SUBSCRIBED" or status == "CHANNEL_SUBSCRIBED":
                    try:
                        # According to docs, we should use send_broadcast
                        if hasattr(channel, 'send_broadcast'):
                            await channel.send_broadcast(
                                'test-event',
                                {"message": "Hello from async test!"}
                            )
                            print("Message sent using channel.send_broadcast()")
                        else:
                            print("Channel does not have send_broadcast method. Available methods:")
                            print([m for m in dir(channel) if not m.startswith('_')])
                            assert False, "send_broadcast method not found on channel"
                    except Exception as broadcast_error:
                        print(f"Error during broadcast in subscription callback: {broadcast_error}")
                        print(f"Error type: {type(broadcast_error).__name__}")
            
            # For AsyncRealtimeChannel, we use on_broadcast instead of on
            channel.on_broadcast(
                'test-event',  # Event name
                handle_broadcast  # Callback function
            )
            
            # Subscribe to the channel with the callback
            await channel.subscribe(on_subscribe)
            print("Subscribed to channel")
            
            # Wait for the message to be received
            start_time = time.time()
            timeout = 5  # 5 seconds timeout
            
            while not received_messages and time.time() - start_time < timeout:
                await asyncio.sleep(0.1)
                print("Waiting for message...")
            
            # Check if we received any messages
            if len(received_messages) > 0:
                print(f"Received messages: {received_messages}")
                assert received_messages[0]["message"] == "Hello from async test!"
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
                
                # Fail the test instead of skipping
                assert False, "No messages received - check Realtime configuration"
            
        except Exception as e:
            print(f"Error in async test: {str(e)}")
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
            
            raise
        finally:
            # Ensure we properly clean up the channel to avoid asyncio errors
            if channel:
                try:
                    # Make sure we unsubscribe from the channel
                    await channel.unsubscribe()
                    # Remove the channel
                    await async_supabase_client.remove_channel(channel)
                except Exception as cleanup_error:
                    print(f"Warning during cleanup: {cleanup_error}")
                    
            # Add a small delay to allow tasks to complete
            await asyncio.sleep(0.5)
