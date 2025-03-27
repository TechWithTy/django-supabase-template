import pytest
import os
import uuid
import time
from unittest.mock import patch

from ..realtime import SupabaseRealtimeService


class TestSupabaseRealtimeService:
    """Tests for the SupabaseRealtimeService class"""

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
    def realtime_service(self, mock_settings):
        """Create a SupabaseRealtimeService instance for testing"""
        return SupabaseRealtimeService()

    @patch.object(SupabaseRealtimeService, "_make_request")
    def test_get_channels(self, mock_make_request, realtime_service):
        """Test getting all channels"""
        # Configure mock response
        mock_make_request.return_value = {
            "channels": [
                {"id": "channel1", "name": "Channel 1"},
                {"id": "channel2", "name": "Channel 2"},
            ]
        }

        # Call get_channels method
        result = realtime_service.get_channels(auth_token="test-token")

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="GET", endpoint="/realtime/v1/channels", auth_token="test-token"
        )

        # Verify result
        assert len(result["channels"]) == 2
        assert result["channels"][0]["id"] == "channel1"
        assert result["channels"][1]["name"] == "Channel 2"

    @patch.object(SupabaseRealtimeService, "_make_request")
    def test_subscribe_to_channel(self, mock_make_request, realtime_service):
        """Test subscribing to a channel"""
        # Configure mock response
        mock_make_request.return_value = {
            "subscription_id": "sub123",
            "channel": "test-channel",
            "status": "subscribed",
        }

        # Call subscribe_to_channel method
        result = realtime_service.subscribe_to_channel(
            channel="test-channel", event="INSERT", auth_token="test-token"
        )

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/realtime/v1/subscribe",
            auth_token="test-token",
            data={"channel": "test-channel", "event": "INSERT"},
        )

        # Verify result
        assert result["subscription_id"] == "sub123"
        assert result["status"] == "subscribed"

    @patch.object(SupabaseRealtimeService, "_make_request")
    def test_unsubscribe_from_channel(self, mock_make_request, realtime_service):
        """Test unsubscribing from a channel"""
        # Configure mock response
        mock_make_request.return_value = {
            "subscription_id": "sub123",
            "status": "unsubscribed",
        }

        # Call unsubscribe_from_channel method
        result = realtime_service.unsubscribe_from_channel(
            subscription_id="sub123", auth_token="test-token"
        )

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/realtime/v1/unsubscribe",
            auth_token="test-token",
            data={"subscription_id": "sub123"},
        )

        # Verify result
        assert result["subscription_id"] == "sub123"
        assert result["status"] == "unsubscribed"

    @patch.object(SupabaseRealtimeService, "_make_request")
    def test_broadcast_message(self, mock_make_request, realtime_service):
        """Test broadcasting a message to a channel"""
        # Configure mock response
        mock_make_request.return_value = {"message_id": "msg123", "status": "delivered"}

        # Call broadcast_message method
        result = realtime_service.broadcast_message(
            channel="test-channel",
            event="CUSTOM",
            payload={"message": "Hello, world!"},
            auth_token="test-token",
        )

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/realtime/v1/broadcast",
            auth_token="test-token",
            data={
                "channel": "test-channel",
                "event": "CUSTOM",
                "payload": {"message": "Hello, world!"},
            },
        )

        # Verify result
        assert result["message_id"] == "msg123"
        assert result["status"] == "delivered"


class TestRealSupabaseRealtimeService:
    """Real-world integration tests for SupabaseRealtimeService
    
    These tests make actual API calls to Supabase and require:
    1. A valid Supabase URL and API keys in env variables
    2. Use of the --integration flag when running tests
    3. A Supabase instance with realtime enabled
    """
    
    @pytest.fixture
    def realtime_service(self):
        """Create a real SupabaseRealtimeService instance"""
        return SupabaseRealtimeService()
    
    @pytest.fixture
    def test_table_name(self):
        """Test table name for realtime tests"""
        return os.getenv("TEST_TABLE_NAME", "test_table")
    
    @pytest.fixture
    def test_channel_name(self):
        """Generate a unique test channel name"""
        return f"test-channel-{uuid.uuid4()}"
    
    @pytest.mark.skipif(
        not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_ANON_KEY"),
        reason="Supabase credentials not set in environment variables",
    )
    def test_real_subscribe_and_broadcast(self, realtime_service, test_channel_name):
        """Test subscribing to a channel and broadcasting a message
        
        Note: This test requires that your Supabase instance has realtime enabled.
        """
        # Skip if not using --integration flag
        if os.getenv("SKIP_INTEGRATION_TESTS", "true").lower() == "true":
            pytest.skip("Integration tests disabled - use --integration flag to run")
        
        try:
            # 1. Subscribe to a test channel
            subscribe_result = realtime_service.subscribe_to_channel(
                channel=test_channel_name,
                event="BROADCAST"
            )
            
            assert subscribe_result is not None
            assert "subscription_id" in subscribe_result
            assert "status" in subscribe_result
            
            subscription_id = subscribe_result["subscription_id"]
            print(f"Successfully subscribed to channel '{test_channel_name}' with subscription ID: {subscription_id}")
            
            # 2. Broadcast a test message
            test_message = {"message": f"Test message {uuid.uuid4()}", "timestamp": time.time()}
            broadcast_result = realtime_service.broadcast_message(
                channel=test_channel_name,
                event="BROADCAST",
                payload=test_message
            )
            
            assert broadcast_result is not None
            print(f"Successfully broadcast message to channel '{test_channel_name}'")
            
            # 3. Unsubscribe from the channel
            unsubscribe_result = realtime_service.unsubscribe_from_channel(
                subscription_id=subscription_id
            )
            
            assert unsubscribe_result is not None
            assert "status" in unsubscribe_result
            print(f"Successfully unsubscribed from channel '{test_channel_name}'")
            
        except Exception as e:
            if "feature is not enabled" in str(e).lower():
                pytest.skip("Realtime feature is not enabled in your Supabase instance")
            else:
                pytest.fail(f"Real-world Supabase realtime test failed: {str(e)}")
    
    @pytest.mark.skipif(
        not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        reason="Supabase credentials not set in environment variables",
    )
    def test_real_table_changes(self, realtime_service, test_table_name):
        """Test subscribing to table changes
        
        Note: This test requires that your Supabase instance has realtime enabled,
        and you have enabled database change events in your project settings.
        You must have a database table with the name specified in TEST_TABLE_NAME.
        """
        # Skip if not using --integration flag
        if os.getenv("SKIP_INTEGRATION_TESTS", "true").lower() == "true":
            pytest.skip("Integration tests disabled - use --integration flag to run")
        
        try:
            # 1. Subscribe to database table changes
            channel_name = f"realtime:public:{test_table_name}"
            
            subscribe_result = realtime_service.subscribe_to_channel(
                channel=channel_name,
                event="*",  # Listen to all events (INSERT, UPDATE, DELETE)
                is_admin=True  # Use admin token for realtime subscription
            )
            
            assert subscribe_result is not None
            assert "subscription_id" in subscribe_result
            
            subscription_id = subscribe_result["subscription_id"]
            print(f"Successfully subscribed to table changes for '{test_table_name}'")
            
            # Note: In a real application, you would set up a listener to handle changes,
            # but for this test, we're just verifying that we can subscribe without errors
            
            # 3. Unsubscribe when done
            unsubscribe_result = realtime_service.unsubscribe_from_channel(
                subscription_id=subscription_id,
                is_admin=True
            )
            
            assert unsubscribe_result is not None
            print(f"Successfully unsubscribed from table changes for '{test_table_name}'")
            
        except Exception as e:
            if "feature is not enabled" in str(e).lower():
                pytest.skip("Realtime feature is not enabled in your Supabase instance")
            elif "table does not exist" in str(e).lower():
                pytest.skip(f"Table '{test_table_name}' does not exist in your Supabase database")
            else:
                pytest.fail(f"Real-world Supabase realtime table changes test failed: {str(e)}")
