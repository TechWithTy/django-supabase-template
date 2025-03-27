import pytest
from unittest.mock import patch, MagicMock
import requests

from apps.supabase._service import SupabaseService


class TestSupabaseService:
    """Tests for the SupabaseService base class"""

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
    def service(self, mock_settings):
        """Create a SupabaseService instance for testing"""
        return SupabaseService()
    
    def test_init(self, service):
        """Test initialization of SupabaseService"""
        assert service.base_url == 'https://example.supabase.co'
        assert service.anon_key == 'test-anon-key'
        assert service.service_role_key == 'test-service-role-key'
    
    def test_get_headers_anonymous(self, service):
        """Test getting headers for anonymous requests"""
        headers = service._get_headers()
        
        assert headers['Content-Type'] == 'application/json'
        assert headers['apikey'] == 'test-anon-key'
        assert 'Authorization' not in headers
    
    def test_get_headers_with_auth(self, service):
        """Test getting headers with auth token"""
        headers = service._get_headers(auth_token='test-token')
        
        assert headers['Content-Type'] == 'application/json'
        assert headers['apikey'] == 'test-anon-key'
        assert headers['Authorization'] == 'Bearer test-token'
    
    def test_get_headers_admin(self, service):
        """Test getting headers for admin requests"""
        headers = service._get_headers(is_admin=True)
        
        assert headers['Content-Type'] == 'application/json'
        assert headers['apikey'] == 'test-service-role-key'
        assert headers['Authorization'] == 'Bearer test-service-role-key'
    
    @patch('apps.supabase._service.requests.request')
    def test_make_request_success(self, mock_request, service):
        """Test making a successful request"""
        # Configure mock response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'data': 'test-data'}
        mock_response.content = b'{"data": "test-data"}'
        mock_request.return_value = mock_response
        
        # Make request
        result = service._make_request(
            method='GET',
            endpoint='/test-endpoint',
            auth_token='test-token',
            data={'test': 'data'},
            params={'param': 'value'}
        )
        
        # Verify request was made correctly
        mock_request.assert_called_once_with(
            method='GET',
            url='https://example.supabase.co/test-endpoint',
            headers={
                'Content-Type': 'application/json',
                'apikey': 'test-anon-key',
                'Authorization': 'Bearer test-token'
            },
            json={'test': 'data'},
            params={'param': 'value'},
            timeout=30
        )
        
        # Verify result
        assert result == {'data': 'test-data'}
    
    @patch('apps.supabase._service.requests.request')
    def test_make_request_http_error(self, mock_request, service):
        """Test making a request that results in an HTTP error"""
        # Configure mock response
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_response.json.return_value = {'error': 'Not found'}
        mock_response.status_code = 404
        mock_response.text = 'Not found'
        mock_request.return_value = mock_response
        
        # Make request and verify exception
        with pytest.raises(Exception) as excinfo:
            service._make_request(
                method='GET',
                endpoint='/test-endpoint'
            )
        
        assert 'Supabase API error' in str(excinfo.value)
    
    @patch('apps.supabase._service.requests.request')
    def test_make_request_general_error(self, mock_request, service):
        """Test making a request that results in a general error"""
        # Configure mock to raise exception
        mock_request.side_effect = Exception("Connection error")
        
        # Make request and verify exception
        with pytest.raises(Exception) as excinfo:
            service._make_request(
                method='GET',
                endpoint='/test-endpoint'
            )
        
        assert 'Unexpected error during Supabase request' in str(excinfo.value)
