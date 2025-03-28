import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestEdgeFunctionsViews:
    """Integration tests for Supabase Edge Functions endpoints"""

    def test_list_edge_functions(self, authenticated_client, supabase_services):
        """Test listing edge functions with real Supabase API"""
        url = reverse('users:edge-functions-list')
        response = authenticated_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert 'data' in response.data
        # The actual data will depend on what edge functions are available in your Supabase project
        # Just check that we got a list back, even if it's empty
        assert isinstance(response.data['data'], list)
        
    def test_get_edge_function(self, authenticated_client, supabase_services):
        """Test getting a specific edge function with real Supabase API"""
        # First get the list of functions to find a valid function_id
        list_url = reverse('users:edge-functions-list')
        list_response = authenticated_client.get(list_url)
        
        # Skip the test if no functions are available
        if not list_response.data['data']:
            pytest.skip("No edge functions available for testing")
        
        # Get the first function ID
        function_id = list_response.data['data'][0]['id']
        
        # Now test getting that specific function
        url = reverse('users:edge-functions-get', kwargs={'function_id': function_id})
        response = authenticated_client.get(url)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert 'data' in response.data
        assert response.data['data']['id'] == function_id
        
    def test_invoke_edge_function(self, authenticated_client, supabase_services):
        """Test invoking an edge function with real Supabase API"""
        # First get the list of functions to find a valid function_id
        list_url = reverse('users:edge-functions-list')
        list_response = authenticated_client.get(list_url)
        
        # Skip the test if no functions are available
        if not list_response.data['data']:
            pytest.skip("No edge functions available for testing")
        
        # Get the first function ID
        function_id = list_response.data['data'][0]['id']
        
        # Test data to send to the function
        # Using minimal data that should work with most functions
        data = {"test": True}
        
        # Make request to invoke the function
        url = reverse('users:edge-functions-invoke', kwargs={'function_id': function_id})
        response = authenticated_client.post(url, data, format='json')
        
        # Assertions - note that we can't know what the function will return
        # so we just check that the call succeeded
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        assert 'data' in response.data
