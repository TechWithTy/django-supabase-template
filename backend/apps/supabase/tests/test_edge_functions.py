import pytest
from unittest.mock import patch, MagicMock

from ..edge_functions import SupabaseEdgeFunctionsService


class TestSupabaseEdgeFunctionsService:
    """Tests for the SupabaseEdgeFunctionsService class"""

    @pytest.fixture
    def edge_functions_service(self):
        """Create a SupabaseEdgeFunctionsService instance for testing"""
        with patch('apps.supabase.service.settings') as mock_settings:
            # Configure mock settings
            mock_settings.SUPABASE_DB_CONNECTION_STRING = 'https://example.supabase.co'
            mock_settings.SUPABASE_ANON_KEY = 'test-anon-key'
            mock_settings.SUPABASE_SERVICE_ROLE_KEY = 'test-service-role-key'
            
            edge_functions_service = SupabaseEdgeFunctionsService()
            return edge_functions_service
    
    @patch.object(SupabaseEdgeFunctionsService, '_make_request')
    def test_invoke_function_without_params(self, mock_make_request, edge_functions_service):
        """Test invoking an edge function without parameters"""
        # Configure mock response
        mock_make_request.return_value = {
            'result': 'Function executed successfully'
        }
        
        # Call invoke_function method
        result = edge_functions_service.invoke_function(
            function_name='test-function',
            auth_token='test-token'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='POST',
            endpoint='/functions/v1/test-function',
            auth_token='test-token',
            data=None
        )
        
        # Verify result
        assert result['result'] == 'Function executed successfully'
    
    @patch.object(SupabaseEdgeFunctionsService, '_make_request')
    def test_invoke_function_with_params(self, mock_make_request, edge_functions_service):
        """Test invoking an edge function with parameters"""
        # Configure mock response
        mock_make_request.return_value = {
            'result': 'Function executed with parameters',
            'params': {'param1': 'value1', 'param2': 'value2'}
        }
        
        # Call invoke_function method with parameters
        result = edge_functions_service.invoke_function(
            function_name='test-function',
            params={'param1': 'value1', 'param2': 'value2'},
            auth_token='test-token'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='POST',
            endpoint='/functions/v1/test-function',
            auth_token='test-token',
            data={'param1': 'value1', 'param2': 'value2'}
        )
        
        # Verify result
        assert result['result'] == 'Function executed with parameters'
        assert result['params']['param1'] == 'value1'
    
    @patch.object(SupabaseEdgeFunctionsService, '_make_request')
    def test_invoke_function_with_admin_token(self, mock_make_request, edge_functions_service):
        """Test invoking an edge function with admin token"""
        # Configure mock response
        mock_make_request.return_value = {
            'result': 'Function executed with admin privileges'
        }
        
        # Call invoke_function method with is_admin=True
        result = edge_functions_service.invoke_function(
            function_name='test-function',
            is_admin=True
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='POST',
            endpoint='/functions/v1/test-function',
            auth_token=None,
            data=None,
            is_admin=True
        )
        
        # Verify result
        assert result['result'] == 'Function executed with admin privileges'
