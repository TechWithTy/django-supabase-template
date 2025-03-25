import json
from typing import Any, Dict, List, Optional, Union

import requests
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger('apps.supabase')

class SupabaseService:
    """
    Service class for interacting with Supabase API.
    
    This class provides methods for interacting with various Supabase services:
    - Auth (user management)
    - Database (PostgreSQL)
    - Storage
    - Edge Functions
    - Realtime
    
    It handles authentication, request formatting, and response parsing.
    """
    
    def __init__(self):
        self.base_url = settings.SUPABASE_URL
        self.anon_key = settings.SUPABASE_ANON_KEY
        self.service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
        
    def _get_headers(self, auth_token: Optional[str] = None, is_admin: bool = False) -> Dict[str, str]:
        """
        Get the headers for a Supabase API request.
        
        Args:
            auth_token: Optional JWT token for authenticated requests
            is_admin: Whether to use the service role key (admin access)
            
        Returns:
            Dict of headers
        """
        headers = {
            'Content-Type': 'application/json',
            'apikey': self.service_role_key if is_admin else self.anon_key,
        }
        
        if auth_token:
            headers['Authorization'] = f'Bearer {auth_token}'
        elif is_admin:
            # Use service role key as bearer token for admin operations
            headers['Authorization'] = f'Bearer {self.service_role_key}'
            
        return headers
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        auth_token: Optional[str] = None,
        is_admin: bool = False,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a request to the Supabase API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint path
            auth_token: Optional JWT token for authenticated requests
            is_admin: Whether to use the service role key (admin access)
            data: Optional request body data
            params: Optional query parameters
            headers: Optional additional headers
            
        Returns:
            Response data as dictionary
            
        Raises:
            Exception: If the request fails
        """
        url = f"{self.base_url}{endpoint}"
        
        # Get default headers and merge with any additional headers
        request_headers = self._get_headers(auth_token, is_admin)
        if headers:
            request_headers.update(headers)
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=request_headers,
                json=data,
                params=params
            )
            
            # Raise exception for error status codes
            response.raise_for_status()
            
            # Return JSON response if available, otherwise return empty dict
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Supabase API error: {str(e)}")
            # Try to get error details from response
            error_detail = {}
            try:
                error_detail = response.json()
            except Exception:
                error_detail = {'status': response.status_code, 'message': response.text}
                
            raise Exception(f"Supabase API error: {error_detail}")
            
        except Exception as e:
            logger.error(f"Supabase request error: {str(e)}")
            raise Exception(f"Supabase request error: {str(e)}")
