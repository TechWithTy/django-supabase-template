import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestUtilityViews:
    """Integration tests for Supabase utility endpoints"""

    def test_health_check(self, authenticated_client):
        """Test health check endpoint with real Supabase API"""
        url = reverse('users:utility-health-check')
        response = authenticated_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert 'status' in response.data
        assert response.data['status'] == 'ok'
        assert 'timestamp' in response.data
        
    def test_supabase_connection(self, authenticated_client, supabase_services):
        """Test Supabase connection check endpoint with real Supabase API"""
        url = reverse('users:utility-supabase-connection')
        response = authenticated_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert 'status' in response.data
        assert response.data['status'] == 'connected'
        assert 'timestamp' in response.data
        
    def test_ping_supabase(self, authenticated_client, supabase_services):
        """Test pinging Supabase with real API"""
        url = reverse('users:utility-ping-supabase')
        response = authenticated_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert 'response_time' in response.data
        assert isinstance(response.data['response_time'], float)
        assert response.data['response_time'] > 0
        assert 'timestamp' in response.data
        
    def test_get_db_info(self, authenticated_client, supabase_services):
        """Test getting database information with real Supabase API"""
        url = reverse('users:utility-get-db-info')
        response = authenticated_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert 'db_info' in response.data
        assert 'version' in response.data['db_info']
        assert 'extensions' in response.data['db_info']
        assert isinstance(response.data['db_info']['extensions'], list)
        
    def test_get_server_time(self, authenticated_client):
        """Test getting server time with real Supabase API"""
        url = reverse('users:utility-get-server-time')
        response = authenticated_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert 'server_time' in response.data
        assert 'timestamp' in response.data
        
        # Basic validation that we got a time string back
        server_time_str = response.data['server_time']
        assert len(server_time_str) > 0
        
    def test_get_system_info(self, authenticated_client):
        """Test getting system information with real Supabase API"""
        url = reverse('users:utility-get-system-info')
        response = authenticated_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert 'system_info' in response.data
        assert 'os' in response.data['system_info']
        assert 'python_version' in response.data['system_info']
        assert 'django_version' in response.data['system_info']
        assert 'database' in response.data['system_info']
        
    def test_get_auth_config(self, authenticated_client):
        """Test getting auth configuration with real Supabase API"""
        url = reverse('users:utility-get-auth-config')
        response = authenticated_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert 'auth_config' in response.data
        assert 'providers' in response.data['auth_config']
        assert isinstance(response.data['auth_config']['providers'], list)
        
    def test_get_storage_config(self, authenticated_client):
        """Test getting storage configuration with real Supabase API"""
        url = reverse('users:utility-get-storage-config')
        response = authenticated_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert 'storage_config' in response.data
        assert 'bucket_size_limit' in response.data['storage_config']
        assert 'file_size_limit' in response.data['storage_config']
