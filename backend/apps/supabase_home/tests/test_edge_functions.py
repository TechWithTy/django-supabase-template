import pytest
import os
from unittest.mock import patch

from ..edge_functions import SupabaseEdgeFunctionsService


class TestSupabaseEdgeFunctionsService:
    """Tests for the SupabaseEdgeFunctionsService class"""

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
    def edge_functions_service(self, mock_settings):
        """Create a SupabaseEdgeFunctionsService instance for testing"""
        return SupabaseEdgeFunctionsService()

    @patch.object(SupabaseEdgeFunctionsService, "_make_request")
    def test_invoke_function_without_params(
        self, mock_make_request, edge_functions_service
    ):
        """Test invoking an edge function without parameters"""
        # Configure mock response
        mock_make_request.return_value = {"result": "Function executed successfully"}

        # Call invoke_function method
        result = edge_functions_service.invoke_function(
            function_name="test-function", auth_token="test-token"
        )

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/functions/v1/test-function",
            auth_token="test-token",
            data=None,
        )

        # Verify result
        assert result["result"] == "Function executed successfully"

    @patch.object(SupabaseEdgeFunctionsService, "_make_request")
    def test_invoke_function_with_params(
        self, mock_make_request, edge_functions_service
    ):
        """Test invoking an edge function with parameters"""
        # Configure mock response
        mock_make_request.return_value = {
            "result": "Function executed with parameters",
            "params": {"param1": "value1", "param2": "value2"},
        }

        # Call invoke_function method with parameters
        result = edge_functions_service.invoke_function(
            function_name="test-function",
            params={"param1": "value1", "param2": "value2"},
            auth_token="test-token",
        )

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/functions/v1/test-function",
            auth_token="test-token",
            data={"param1": "value1", "param2": "value2"},
        )

        # Verify result
        assert result["result"] == "Function executed with parameters"
        assert result["params"]["param1"] == "value1"

    @patch.object(SupabaseEdgeFunctionsService, "_make_request")
    def test_invoke_function_with_admin_token(
        self, mock_make_request, edge_functions_service
    ):
        """Test invoking an edge function with admin token"""
        # Configure mock response
        mock_make_request.return_value = {
            "result": "Function executed with admin privileges"
        }

        # Call invoke_function method with is_admin=True
        result = edge_functions_service.invoke_function(
            function_name="test-function", is_admin=True
        )

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/functions/v1/test-function",
            auth_token=None,
            data=None,
            is_admin=True,
        )

        # Verify result
        assert result["result"] == "Function executed with admin privileges"


class TestRealSupabaseEdgeFunctionsService:
    """Real-world integration tests for SupabaseEdgeFunctionsService
    
    These tests make actual API calls to Supabase and require:
    1. A valid Supabase URL and API keys in env variables
    2. Use of the --integration flag when running tests
    3. Deployed edge function(s) in your Supabase project
    """
    
    @pytest.fixture
    def edge_functions_service(self):
        """Create a real SupabaseEdgeFunctionsService instance"""
        return SupabaseEdgeFunctionsService()
    
    @pytest.fixture
    def test_function_name(self):
        """Get test function name from environment or use default"""
        return os.getenv("TEST_EDGE_FUNCTION_NAME", "hello-world")
    
    @pytest.mark.skipif(
        not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        reason="Supabase credentials not set in environment variables",
    )
    def test_real_invoke_function(self, edge_functions_service, test_function_name):
        """Test invoking an edge function with real Supabase API"""
        # Skip if not using --integration flag
        if os.getenv("SKIP_INTEGRATION_TESTS", "true").lower() == "true":
            pytest.skip("Integration tests disabled - use --integration flag to run")
            
        try:
            # Try to invoke the function with admin privileges
            result = edge_functions_service.invoke_function(
                function_name=test_function_name,
                is_admin=True,
                params={"message": "Hello from test"}
            )
            
            # Verify a result was returned
            assert result is not None, "Edge function invocation returned None"
            
            # Print the result for debugging
            print(f"Edge function '{test_function_name}' response: {result}")
            
        except Exception as e:
            if "Function not found" in str(e):
                pytest.skip(f"Edge function '{test_function_name}' not found in your Supabase project")
            else:
                pytest.fail(f"Real-world Supabase edge function test failed: {str(e)}")
