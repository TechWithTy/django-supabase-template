from typing import Any, Dict, Optional

from ._service import SupabaseService

class SupabaseEdgeFunctionsService(SupabaseService):
    """
    Service for interacting with Supabase Edge Functions.
    
    This class provides methods for invoking Edge Functions deployed to Supabase.
    """
    
    def invoke_function(self, 
                       function_name: str, 
                       invoke_method: str = "POST",
                       body: Optional[Dict[str, Any]] = None,
                       headers: Optional[Dict[str, str]] = None,
                       auth_token: Optional[str] = None) -> Any:
        """
        Invoke a Supabase Edge Function.
        
        Args:
            function_name: Name of the function to invoke
            invoke_method: HTTP method to use (GET, POST, etc.)
            body: Optional request body
            headers: Optional additional headers
            auth_token: Optional JWT token for authenticated requests
            
        Returns:
            Function response
        """
        endpoint = f"/functions/v1/{function_name}"
        
        # Get default headers and merge with any additional headers
        request_headers = self._get_headers(auth_token)
        if headers:
            request_headers.update(headers)
            
        return self._make_request(
            method=invoke_method,
            endpoint=endpoint,
            auth_token=auth_token,
            data=body,
            headers=request_headers
        )
