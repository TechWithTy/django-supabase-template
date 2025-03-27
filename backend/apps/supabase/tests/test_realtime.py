import pytest
from unittest.mock import patch, MagicMock

from ..realtime import SupabaseRealtimeService


class TestSupabaseRealtimeService:
    """Tests for the SupabaseRealtimeService class"""

    @pytest.fixture
    def realtime_service(self):
        """Create a SupabaseRealtimeService instance for testing"""
        with patch('apps.supabase.service.settings') as mock_settings:
            # Configure mock settings
            mock_settings.SUPABASE_DB_CONNECTION_STRING = 'https://example.supabase.co'
            mock_settings.SUPABASE_ANON_KEY = 'test-anon-key'
            mock_settings.SUPABASE_SERVICE_ROLE_KEY = 'test-service-role-key'
            
            realtime_service = SupabaseRealtimeService()
            return realtime_service
    
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
    def test_get_channel(self, mock_make_request, realtime_service):
        """Test getting a specific channel"""
        # Configure mock response
        mock_make_request.return_value = {
            'id': 'test-channel',
            'name': 'Test Channel',
            'subscribers': 5
        }
        
        # Call get_channel method
        result = realtime_service.get_channel(
            channel_id='test-channel',
            auth_token='test-token'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='GET',
            endpoint='/realtime/v1/channels/test-channel',
            auth_token='test-token'
        )
        
        # Verify result
        assert result['id'] == 'test-channel'
        assert result['subscribers'] == 5
    
    @patch.object(SupabaseRealtimeService, '_make_request')
    def test_create_channel(self, mock_make_request, realtime_service):
        """Test creating a channel"""
        # Configure mock response
        mock_make_request.return_value = {
            'id': 'new-channel',
            'name': 'New Channel',
            'subscribers': 0
        }
        
        # Call create_channel method
        result = realtime_service.create_channel(
            channel_id='new-channel',
            auth_token='test-token'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='POST',
            endpoint='/realtime/v1/channels',
            auth_token='test-token',
            data={'id': 'new-channel'}
        )
        
        # Verify result
        assert result['id'] == 'new-channel'
        assert result['subscribers'] == 0
    
    @patch.object(SupabaseRealtimeService, '_make_request')
    def test_delete_channel(self, mock_make_request, realtime_service):
        """Test deleting a channel"""
        # Configure mock response
        mock_make_request.return_value = {}
        
        # Call delete_channel method
        realtime_service.delete_channel(
            channel_id='test-channel',
            auth_token='test-token'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='DELETE',
            endpoint='/realtime/v1/channels/test-channel',
            auth_token='test-token'
        )
    
    @patch.object(SupabaseRealtimeService, '_make_request')
    def test_subscribe_to_channel(self, mock_make_request, realtime_service):
        """Test subscribing to a channel"""
        # Configure mock response
        mock_make_request.return_value = {
            'subscription_id': 'sub123',
            'channel_id': 'test-channel',
            'status': 'subscribed'
        }
        
        # Call subscribe_to_channel method
        result = realtime_service.subscribe_to_channel(
            channel_id='test-channel',
            event_types=['INSERT', 'UPDATE'],
            auth_token='test-token'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='POST',
            endpoint='/realtime/v1/channels/test-channel/subscribe',
            auth_token='test-token',
            data={'event_types': ['INSERT', 'UPDATE']}
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
            channel_id='test-channel',
            subscription_id='sub123',
            auth_token='test-token'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='DELETE',
            endpoint='/realtime/v1/channels/test-channel/subscriptions/sub123',
            auth_token='test-token'
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
            channel_id='test-channel',
            event_type='CUSTOM',
            payload={'message': 'Hello, world!'},
            auth_token='test-token'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='POST',
            endpoint='/realtime/v1/channels/test-channel/broadcast',
            auth_token='test-token',
            data={
                'event_type': 'CUSTOM',
                'payload': {'message': 'Hello, world!'}
            }
        )
        
        # Verify result
        assert result['message_id'] == 'msg123'
        assert result['status'] == 'delivered'
