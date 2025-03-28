import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestHealthCheckViews:
    """Integration tests for health check endpoints using real Supabase connections"""

    def test_health_check(self, authenticated_client):
        """Test health check endpoint with real Supabase API"""
        url = reverse('users:health-check')
        response = authenticated_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert "status" in response.data
        assert response.data["status"] == "ok"
        assert "timestamp" in response.data
        
    def test_health_check_supabase(self, authenticated_client, supabase_services):
        """Test Supabase health check with real connection"""
        url = reverse('users:health-check-supabase')
        response = authenticated_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert "status" in response.data
        assert "version" in response.data
        assert "timestamp" in response.data
