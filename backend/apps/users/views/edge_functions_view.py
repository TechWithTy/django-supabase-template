from typing import Any, Dict, Optional

from django.conf import settings
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

# Import the SupabaseEdgeFunctionsService directly
from apps.supabase.edge_functions import SupabaseEdgeFunctionsService

# Initialize the edge functions service
edge_functions_service = SupabaseEdgeFunctionsService()


@api_view(["POST", "GET", "PUT", "DELETE", "PATCH"])
@permission_classes([permissions.IsAuthenticated])
def invoke_function(request: Request) -> Response:
    """
    Invoke a Supabase Edge Function.
    
    Request body (for POST, PUT, PATCH):
    - function_name: Name of the function to invoke (required)
    - body: Optional request body to send to the function
    - headers: Optional additional headers to include
    
    Query parameters (for GET, DELETE):
    - function_name: Name of the function to invoke (required)
    """
    # Extract function name from request body or query parameters based on method
    if request.method in ["POST", "PUT", "PATCH"]:
        function_name = request.data.get("function_name")
        body = request.data.get("body")
        headers = request.data.get("headers")
    else:  # GET, DELETE
        function_name = request.query_params.get("function_name")
        body = None
        headers = None
    
    if not function_name:
        return Response(
            {"error": "Function name is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    try:
        # Get auth token if available
        auth_token = request.auth.token if hasattr(request, 'auth') and hasattr(request.auth, 'token') else None
        
        response = edge_functions_service.invoke_function(
            function_name=function_name,
            invoke_method=request.method,
            body=body,
            headers=headers,
            auth_token=auth_token
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to invoke edge function: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def list_functions(request: Request) -> Response:
    """
    List all available Edge Functions.
    
    This is a placeholder endpoint since Supabase doesn't provide a direct API
    to list functions. In a real implementation, you might want to maintain a
    registry of functions in your database or fetch this information from
    Supabase's management API if available.
    """
    # This is a placeholder implementation
    # In a real-world scenario, you would fetch this from your database or Supabase
    functions = [
        {
            "name": "example-function",
            "description": "An example edge function",
            "methods": ["GET", "POST"],
        }
        # Add more functions as they become available
    ]
    
    return Response(functions, status=status.HTTP_200_OK)
