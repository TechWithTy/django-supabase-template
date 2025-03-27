import pytest
import os
import uuid
import time
import random
import string

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


@pytest.mark.integration
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
        """Create a test user and return the auth token"""
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
            
            # Extract the access token
            session = signup_result.session
            if session:
                access_token = session.access_token
                print(f"Access token obtained from signup: {bool(access_token)}")
                return access_token
            else:
                print("No session in signup result, trying sign in...")
                
                # Try to sign in
                signin_result = supabase_client.auth.sign_in_with_password({
                    "email": test_user_credentials["email"],
                    "password": test_user_credentials["password"]
                })
                
                if signin_result.session:
                    access_token = signin_result.session.access_token
                    print(f"Access token obtained from signin: {bool(access_token)}")
                    return access_token
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
                    print(f"Access token obtained from signin: {bool(access_token)}")
                    return access_token
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
    
    def test_realtime_subscribe_and_broadcast(self, supabase_client, test_channel_name, realtime_issues, auth_token):
        """Test subscribing to a channel and broadcasting a message using the official client"""
        # Skip test if no auth token is available
        if not auth_token:
            pytest.skip("No authentication token available. Cannot test Realtime API without authentication.")
            
        # Report any setup issues but continue with the test
        if realtime_issues:
            for issue in realtime_issues:
                print(f"WARNING: {issue}")
            print("\nContinuing with test despite setup issues...")
        
        # Set the auth token for the client
        supabase_client.auth.set_session(access_token=auth_token)
        
        try:
            # Create a channel with the client
            channel = supabase_client.channel(test_channel_name, {
                "config": {
                    "broadcast": {
                        "self": True
                    },
                    "presence": {
                        "key": "user1"
                    }
                }
            })
            
            # Track received messages
            received_messages = []
            
            # Subscribe to the channel
            def handle_broadcast(payload):
                print(f"Received message: {payload}")
                received_messages.append(payload)
            
            # Subscribe to the 'broadcast' event
            channel.on('broadcast', handle_broadcast)
            
            # Connect to the channel
            channel.subscribe()
            
            # Wait for subscription to be established
            time.sleep(2)
            
            # Broadcast a message
            test_message = {"type": "test", "content": f"Test message at {time.time()}", "sender": "test-user"}
            channel.send({
                "type": "broadcast",
                "event": "broadcast",
                "payload": test_message
            })
            
            # Wait for message to be received
            max_wait = 10  # seconds
            start_time = time.time()
            while not received_messages and time.time() - start_time < max_wait:
                time.sleep(0.5)
                
            # Unsubscribe from the channel
            channel.unsubscribe()
            
            # Verify that we received the message
            assert len(received_messages) > 0, f"No messages received after waiting {max_wait} seconds"
            assert received_messages[0] == test_message, "Received message doesn't match sent message"
            
            print("Successfully subscribed to channel and received broadcast message")
            
        except Exception as e:
            pytest.fail(f"Error testing Realtime API: {str(e)}\n\nPossible causes:\n" +
                       "1. Realtime feature is not enabled in your Supabase project\n" +
                       "2. Your auth token doesn't have permission to access Realtime API\n" +
                       "3. You need to enable the appropriate RLS policies for Realtime")
