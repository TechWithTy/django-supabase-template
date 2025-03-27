import pytest
from unittest.mock import patch

from ..realtime import SupabaseRealtimeService


class TestSupabaseRealtimeService:
    """Tests for the SupabaseRealtimeService class"""

    @pytest.fixture
    def mock_settings(self):
        """Mock Django settings"""
        with patch('apps.supabase._service.settings') as mock_settings:
            # Configure mock settings
            mock_settings.SUPABASE_URL = 'https://example.supabase.co'
            mock_settings.SUPABASE_ANON_KEY = 'test-anon-key'
            mock_settings.SUPABASE_SERVICE_ROLE_KEY = 'test-service-role-key'
            yield mock_settings
    
    @pytest.fixture
    def realtime_service(self, mock_settings):
        """Create a SupabaseRealtimeService instance for testing"""
        return SupabaseRealtimeService()
    
    @patch.object(SupabaseRealtimeService, '_make_request')
    def test_get_channels(self, mock_make_request, realtime_service):
        """Test getting all channels"""
        # Configure mock response
        mock_make_request.return_value = {
            'channels': [
                {'id': 'channel1', 'name': 'Channel 1'},
                {'id': 'channel2', 'name': 'Channel 2'}
            ]
        }
        
        # Call get_channels method
        result = realtime_service.get_channels(auth_token='test-token')
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='GET',
            endpoint='/realtime/v1/channels',
            auth_token='test-token'
        )
        
        # Verify result
        assert len(result['channels']) == 2
        assert result['channels'][0]['id'] == 'channel1'
        assert result['channels'][1]['name'] == 'Channel 2'
    
    @patch.object(SupabaseRealtimeService, '_make_request')
    def test_subscribe_to_channel(self, mock_make_request, realtime_service):
        """Test subscribing to a channel"""
        # Configure mock response
        mock_make_request.return_value = {
            'subscription_id': 'sub123',
            'channel': 'test-channel',
            'status': 'subscribed'
        }
        
        # Call subscribe_to_channel method
        result = realtime_service.subscribe_to_channel(
            channel='test-channel',
            event='INSERT',
            auth_token='test-token'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='POST',
            endpoint='/realtime/v1/subscribe',
            auth_token='test-token',
            data={
                'channel': 'test-channel',
                'event': 'INSERT'
            }
        )
        
        # Verify result
        assert result['subscription_id'] == 'sub123'
        assert result['status'] == 'subscribed'
    
    @patch.object(SupabaseRealtimeService, '_make_request')
    def test_unsubscribe_from_channel(self, mock_make_request, realtime_service):
        """Test unsubscribing from a channel"""
        # Configure mock response
        mock_make_request.return_value = {
            'subscription_id': 'sub123',
            'status': 'unsubscribed'
        }
        
        # Call unsubscribe_from_channel method
        result = realtime_service.unsubscribe_from_channel(
            subscription_id='sub123',
            auth_token='test-token'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='POST',
            endpoint='/realtime/v1/unsubscribe',
            auth_token='test-token',
            data={
                'subscription_id': 'sub123'
            }
        )
        
        # Verify result
        assert result['subscription_id'] == 'sub123'
        assert result['status'] == 'unsubscribed'
    
    @patch.object(SupabaseRealtimeService, '_make_request')
    def test_broadcast_message(self, mock_make_request, realtime_service):
        """Test broadcasting a message to a channel"""
        # Configure mock response
        mock_make_request.return_value = {
            'message_id': 'msg123',
            'status': 'delivered'
        }
        
        # Call broadcast_message method
        result = realtime_service.broadcast_message(
            channel='test-channel',
            event='CUSTOM',
            payload={'message': 'Hello, world!'},
            auth_token='test-token'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='POST',
            endpoint='/realtime/v1/broadcast',
            auth_token='test-token',
            data={
                'channel': 'test-channel',
                'event': 'CUSTOM',
                'payload': {'message': 'Hello, world!'}
            }
        )
        
        # Verify result
        assert result['message_id'] == 'msg123'
        assert result['status'] == 'delivered'
