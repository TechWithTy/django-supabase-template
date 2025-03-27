import os
import uuid
from unittest.mock import patch, ANY

import pytest

from apps.supabase_home.edge_functions import SupabaseEdgeFunctionsService


class TestSupabaseEdgeFunctionsService:
    """Unit tests for SupabaseEdgeFunctionsService using mocks"""
    
    def setup_method(self):
        self.service = SupabaseEdgeFunctionsService()

    @patch.object(SupabaseEdgeFunctionsService, "_make_request")
    def test_invoke_function_without_params(self, mock_make_request):
        # Setup mock
        mock_make_request.return_value = {"message": "Success"}
        
        # Call the function
        result = self.service.invoke_function(
            function_name="test-function",
            auth_token="test-token"
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/functions/v1/test-function",
            auth_token="test-token",
            is_admin=False,
            data=None,
            headers=ANY
        )
        
        # Verify result
        assert result == {"message": "Success"}

    @patch.object(SupabaseEdgeFunctionsService, "_make_request")
    def test_invoke_function_with_body(self, mock_make_request):
        # Setup mock
        mock_make_request.return_value = {"message": "Success with params"}
        
        # Call the function
        result = self.service.invoke_function(
            function_name="test-function",
            body={"param1": "value1", "param2": "value2"},
            auth_token="test-token"
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/functions/v1/test-function",
            auth_token="test-token",
            is_admin=False,
            data={"param1": "value1", "param2": "value2"},
            headers=ANY
        )
        
        # Verify result
        assert result == {"message": "Success with params"}

    @patch.object(SupabaseEdgeFunctionsService, "_make_request")
    def test_invoke_function_with_admin_token(self, mock_make_request):
        # Setup mock
        mock_make_request.return_value = {"message": "Admin success"}
        
        # Call the function
        result = self.service.invoke_function(
            function_name="test-function",
            is_admin=True
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/functions/v1/test-function",
            auth_token=None,
            is_admin=True,
            data=None,
            headers=ANY
        )
        
        # Verify result
        assert result == {"message": "Admin success"}


@pytest.mark.skipif(not os.environ.get("SUPABASE_URL") or 
                   not os.environ.get("SUPABASE_SERVICE_ROLE_KEY"),
                   reason="Supabase credentials not available")
class TestRealSupabaseEdgeFunctionsService:
    @pytest.fixture
    def edge_functions_service(self):
        return SupabaseEdgeFunctionsService()
    
    def test_real_invoke_function(self, edge_functions_service):
        """
        Test invoking a real function that already exists in your Supabase project.
        
        Note: This test assumes that you have already created a function named 'hello-world'
        in your Supabase project using the Supabase Dashboard or CLI.
        """
        try:
            # Try to invoke a function that should already exist in your project
            # Replace 'hello-world' with the name of a function that exists in your project
            function_name = "hello-world"  # Change this to match your existing function
            
            result = edge_functions_service.invoke_function(
                function_name=function_name,
                invoke_method="GET"  # Adjust method as needed for your function
            )
            
            # Print the result for debugging
            print(f"Function invoked: {result}")
            
            # Basic assertion that we got some kind of response
            assert result is not None, "Expected a response from the function"
            
        except Exception as e:
            # If the function doesn't exist, the test will be skipped rather than fail
            if "404" in str(e) and "not found" in str(e).lower():
                pytest.skip(f"Function '{function_name}' not found in your Supabase project. Create it first or use a different name.")
            else:
                pytest.fail(f"Real-world Supabase function invocation failed: {str(e)}")
    
    def test_mock_management_functions(self, edge_functions_service):
        """
        Test that the mock implementations of management functions work as expected.
        """
        # Generate a unique function name for testing
        function_name = f"test-function-{uuid.uuid4().hex[:8]}"
        
        # Test list_functions (mock)
        functions = edge_functions_service.list_functions()
        assert isinstance(functions, list)
        
        # Test create_function (mock)
        create_result = edge_functions_service.create_function(
            name=function_name,
            source_code="export default () => new Response('Hello');",
            verify_jwt=False
        )
        assert create_result["name"] == function_name
        assert create_result["status"] == "MOCK_CREATED"
        
        # Test get_function (mock)
        get_result = edge_functions_service.get_function(function_name)
        assert get_result["name"] == function_name
        assert get_result["status"] == "MOCK_ACTIVE"
        
        # Test update_function (mock)
        update_result = edge_functions_service.update_function(
            function_name=function_name,
            source_code="export default () => new Response('Updated');"
        )
        assert update_result["name"] == function_name
        assert update_result["status"] == "MOCK_UPDATED"
        
        # Test delete_function (mock)
        delete_result = edge_functions_service.delete_function(function_name)
        assert delete_result["name"] == function_name
        assert delete_result["status"] == "MOCK_DELETED"
