import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestClientViews:
    """Integration tests for Supabase client endpoints"""

    def test_get_supabase_url(self, authenticated_client):
        """Test the get Supabase URL endpoint"""
        url = reverse('users:client-url')
        response = authenticated_client.get(url)

        # Check response
        assert response.status_code == status.HTTP_200_OK
        assert 'supabase_url' in response.data
        assert response.data['supabase_url'].startswith('http')

    def test_get_supabase_anon_key(self, authenticated_client):
        """Test the get Supabase anon key endpoint"""
        url = reverse('users:client-anon-key')
        response = authenticated_client.get(url)

        # Check response
        assert response.status_code == status.HTTP_200_OK
        assert 'supabase_anon_key' in response.data
        assert len(response.data['supabase_anon_key']) > 0

    def test_get_supabase_client_info(self, authenticated_client):
        """Test the get Supabase client info endpoint"""
        url = reverse('users:client-info')
        response = authenticated_client.get(url)

        # Check response
        assert response.status_code == status.HTTP_200_OK
        assert 'supabase_url' in response.data
        assert 'supabase_anon_key' in response.data
        assert response.data['supabase_url'].startswith('http')
        assert len(response.data['supabase_anon_key']) > 0
