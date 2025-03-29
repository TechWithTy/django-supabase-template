import json
from typing import Any, Dict, Optional

import requests
from django.conf import settings
import logging

logger = logging.getLogger(" apps.supabase_home")


class SupabaseError(Exception):
    """Base exception for Supabase-related errors"""

    pass


class SupabaseAuthError(SupabaseError):
    """Exception raised for authentication errors"""

    pass


class SupabaseAPIError(SupabaseError):
    """Exception raised for API errors"""

    def __init__(self, message: str, status_code: int = None, details: Dict = None):
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


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
        # Get configuration from settings
        self.base_url = settings.SUPABASE_URL
        self.anon_key = settings.SUPABASE_ANON_KEY
        self.service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY

        # Validate required settings
        if not self.base_url:
            logger.error("SUPABASE_URL is not set in settings")
            raise ValueError("SUPABASE_URL is not set in settings")

        if not self.anon_key:
            logger.error("SUPABASE_ANON_KEY is not set in settings")
            raise ValueError("SUPABASE_ANON_KEY is not set in settings")

        if not self.service_role_key:
            logger.warning(
                "SUPABASE_SERVICE_ROLE_KEY is not set in settings. Admin operations will not work."
            )

    def _get_headers(
        self, auth_token: Optional[str] = None, is_admin: bool = False
    ) -> Dict[str, str]:
        """
        Get the headers for a Supabase API request.

        Args:
            auth_token: Optional JWT token for authenticated requests
            is_admin: Whether to use the service role key (admin access)

        Returns:
            Dict of headers
        """
        headers = {
            "Content-Type": "application/json",
            "apikey": self.service_role_key if is_admin else self.anon_key,
        }

        # For storage operations, we need to set the Authorization header correctly
        # If is_admin is True, we should use the service role key regardless of auth_token
        if is_admin:
            # Use service role key as bearer token for admin operations
            if not self.service_role_key:
                raise SupabaseAuthError(
                    "Service role key is required for admin operations"
                )
            headers["Authorization"] = f"Bearer {self.service_role_key}"
        elif auth_token:
            # Use the provided auth token if not in admin mode
            headers["Authorization"] = f"Bearer {auth_token}"

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
        timeout: int = 30,
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
            timeout: Request timeout in seconds

        Returns:
            Response data as dictionary

        Raises:
            SupabaseAuthError: If there's an authentication error
            SupabaseAPIError: If the API request fails
            SupabaseError: For other Supabase-related errors
            Exception: For unexpected errors
        """
        url = f"{self.base_url}{endpoint}"

        # Get default headers and merge with any additional headers
        request_headers = self._get_headers(auth_token, is_admin)
        if headers:
            request_headers.update(headers)

        # Enhanced logging for debugging
        logger.info(f"Making {method} request to {url}")
        logger.info(f"Headers: {request_headers}")
        if 'Authorization' in request_headers:
            auth_header = request_headers['Authorization']
            logger.info(f"Authorization header: {auth_header[:15]}...")
        else:
            logger.info("No Authorization header found")
        
        logger.info(f"Request data: {data}")
        logger.info(f"Request params: {params}")

        # Ensure data is not None for any requests with application/json content type
        # Supabase API expects a valid JSON body (even if empty) when Content-Type is application/json
        if data is None and 'Content-Type' in request_headers and request_headers['Content-Type'] == 'application/json':
            data = {}
            logger.info("Initialized empty JSON data")

        try:
            logger.debug(f"Making {method} request to {url}")
            response = requests.request(
                method=method,
                url=url,
                headers=request_headers,
                json=data,
                params=params,
                timeout=timeout,
            )

            # Log request details at debug level
            logger.info(f"Request to {url}: {method} - Status: {response.status_code}")
            logger.info(f"Response headers: {response.headers}")
            
            # Log response content for debugging
            try:
                if response.content:
                    logger.info(f"Response content: {response.content[:200]}...")
                    if response.status_code >= 400:
                        logger.error(f"Error response: {response.content}")
            except Exception as e:
                logger.error(f"Error logging response content: {str(e)}")

            # Handle different error scenarios
            if response.status_code == 401 or response.status_code == 403:
                error_detail = self._parse_error_response(response)
                logger.error(f"Authentication error: {error_detail}")
                raise SupabaseAuthError(f"Authentication error: {error_detail}")

            # Raise exception for other error status codes
            response.raise_for_status()

            # Return JSON response if available, otherwise return empty dict
            if response.content:
                return response.json()
            return {}

        except requests.exceptions.HTTPError as e:
            error_detail = self._parse_error_response(response)
            logger.error(f"Supabase API error: {str(e)} - Details: {error_detail}")
            raise SupabaseAPIError(
                message=f"Supabase API error: {str(e)}",
                status_code=response.status_code,
                details=error_detail,
            )

        except requests.exceptions.ConnectionError as e:
            logger.error("Supabase connection error: " + str(e))
            raise SupabaseError(
                "Connection error: Unable to connect to Supabase API. Check your network connection and Supabase URL."
            )

        except requests.exceptions.Timeout as e:
            logger.error(f"Supabase request timeout: {str(e)}")
            raise SupabaseError(
                f"Request timeout: The request to Supabase API timed out after {timeout} seconds."
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Supabase request exception: {str(e)}")
            raise SupabaseError(f"Request error: {str(e)}")

        except SupabaseAuthError as e:
            # Re-raise SupabaseAuthError without wrapping it in a generic Exception
            logger.error(f"Authentication error being re-raised: {str(e)}")
            raise

        except Exception as e:
            logger.exception(f"Unexpected error during Supabase request: {str(e)}")
            raise Exception(f"Unexpected error during Supabase request: {str(e)}")

    def _parse_error_response(self, response: requests.Response) -> Dict:
        """Parse error response from Supabase API

        Args:
            response: Response object from requests

        Returns:
            Dictionary containing error details
        """
        try:
            return response.json()
        except json.JSONDecodeError:
            return {"status": response.status_code, "message": response.text}
