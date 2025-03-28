import pytest
from django.urls import reverse
from rest_framework import status
import os


@pytest.mark.django_db
class TestRealtimeViews:
    """Integration tests for Supabase Realtime service endpoints"""
    
    @pytest.mark.skipif(not os.environ.get('SUPABASE_PROJECT_URL'), reason="Supabase URL not configured")
    def test_get_channels(self, authenticated_client, supabase_client):
        """Test getting realtime channels with real Supabase client"""
        # First create a channel so we have something to list
        channel_name = "test-channel-listing"
        # Use the Supabase client directly to create a channel
        channel = supabase_client.realtime.channel(channel_name, {"broadcast": {"self": True}, "private": True})
        channel.subscribe()
        
        # Make request to the endpoint
        url = reverse('users:realtime-channels')
        response = authenticated_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        
        # Verify we get a list of channels and our test channel is in it
        # The test might still pass even if we get multiple channels as long as ours is there
        assert isinstance(response.data, list)
        
        # Find our test channel in the results
        found_test_channel = False
        for ch in response.data:
            if 'topic' in ch and ch['topic'] == channel_name:
                found_test_channel = True
                break
        
        # Clean up - unsubscribe from the channel
        channel.unsubscribe()
        
        # Assert that we found our test channel
        assert found_test_channel, "Our test channel was not found in the list"
        
    @pytest.mark.skipif(not os.environ.get('SUPABASE_PROJECT_URL'), reason="Supabase URL not configured")
    def test_create_channel(self, authenticated_client):
        """Test creating a realtime channel with real Supabase"""
        # Test data
        data = {
            "name": "test-create-channel",
            "config": {"broadcast": {"self": True}, "private": True}
        }
        
        # Make request
        url = reverse('users:realtime-channel-create')
        response = authenticated_client.post(url, data, format='json')
        
        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data
        assert 'topic' in response.data
        assert response.data['topic'] == "test-create-channel"
        
        # Save channel ID for next test
        channel_id = response.data['id']
        
        # Cleanup - unsubscribe from channel
        cleanup_url = reverse('users:realtime-channel-unsubscribe', kwargs={'channel_id': channel_id})
        authenticated_client.post(cleanup_url)
        
    @pytest.mark.skipif(not os.environ.get('SUPABASE_PROJECT_URL'), reason="Supabase URL not configured")
    def test_get_channel_and_send_message(self, authenticated_client):
        """Test getting a channel and sending a message with real Supabase"""
        # First create a channel to work with
        create_data = {
            "name": "test-channel-detail",
            "config": {"broadcast": {"self": True}, "private": True}
        }
        create_url = reverse('users:realtime-channel-create')
        create_response = authenticated_client.post(create_url, create_data, format='json')
        assert create_response.status_code == status.HTTP_201_CREATED
        channel_id = create_response.data['id']
        
        # Get channel details
        detail_url = reverse('users:realtime-channel-detail', kwargs={'channel_id': channel_id})
        response = authenticated_client.get(detail_url)
        
        # Assertions for get channel
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == channel_id
        assert response.data['topic'] == "test-channel-detail"
        
        # Send a message to the channel
        message_data = {
            "type": "broadcast",
            "event": "test-event",
            "payload": {"message": "Hello World"}
        }
        
        send_url = reverse('users:realtime-channel-send', kwargs={'channel_id': channel_id})
        send_response = authenticated_client.post(send_url, message_data, format='json')
        
        # Assertions for sending message
        assert send_response.status_code == status.HTTP_200_OK
        assert send_response.data['success'] is True
        
        # Cleanup - unsubscribe from channel
        cleanup_url = reverse('users:realtime-channel-unsubscribe', kwargs={'channel_id': channel_id})
        unsubscribe_response = authenticated_client.post(cleanup_url)
        
        # Assertions for unsubscribe
        assert unsubscribe_response.status_code == status.HTTP_200_OK
        assert unsubscribe_response.data['success'] is True
        
    @pytest.mark.skipif(not os.environ.get('SUPABASE_PROJECT_URL'), reason="Supabase URL not configured")
    def test_unsubscribe_channel(self, authenticated_client):
        """Test unsubscribing from a channel with real Supabase"""
        # First create a channel to unsubscribe from
        create_data = {
            "name": "test-channel-unsubscribe",
            "config": {"broadcast": {"self": True}, "private": True}
        }
        create_url = reverse('users:realtime-channel-create')
        create_response = authenticated_client.post(create_url, create_data, format='json')
        assert create_response.status_code == status.HTTP_201_CREATED
        channel_id = create_response.data['id']
        
        # Unsubscribe from the channel
        url = reverse('users:realtime-channel-unsubscribe', kwargs={'channel_id': channel_id})
        response = authenticated_client.post(url)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        
        # Verify channel is no longer accessible
        detail_url = reverse('users:realtime-channel-detail', kwargs={'channel_id': channel_id})
        detail_response = authenticated_client.get(detail_url)
        
        # Should return a 404 or error response since channel should be unsubscribed
        assert detail_response.status_code >= 400
