from typing import Any, Dict, Optional

from ._service import SupabaseService

class SupabaseRealtimeService(SupabaseService):
    """
    Service for interacting with Supabase Realtime API.
    
    This class provides methods for managing Realtime subscriptions.
    Note: This is a server-side implementation and doesn't maintain websocket
    connections. For client-side realtime, use the Supabase JavaScript client.
    """
    
    def subscribe_to_channel(self, 
                           channel: str, 
                           event: str = "*",
                           auth_token: Optional[str] = None,
                           is_admin: bool = True) -> Dict[str, Any]:
        """
        Subscribe to a Realtime channel.
        
        Args:
            channel: Channel name
            event: Event to subscribe to (default: "*" for all events)
            auth_token: Optional JWT token for authenticated requests
            is_admin: Whether to use the service role key (admin access)
            
        Returns:
            Subscription data
        """
        return self._make_request(
            method="POST",
            endpoint="/realtime/v1/subscribe",
            auth_token=auth_token,
            is_admin=is_admin,
            data={
                "channel": channel,
                "event": event,
                "config": {
                    "private": True  # Enable private channel for RLS support
                }
            }
        )
    
    def unsubscribe_from_channel(self, 
                              subscription_id: str,
                              auth_token: Optional[str] = None,
                              is_admin: bool = True) -> Dict[str, Any]:
        """
        Unsubscribe from a Realtime channel.
        
        Args:
            subscription_id: Subscription ID
            auth_token: Optional JWT token for authenticated requests
            is_admin: Whether to use the service role key (admin access)
            
        Returns:
            Success message
        """
        return self._make_request(
            method="POST",
            endpoint="/realtime/v1/unsubscribe",
            auth_token=auth_token,
            is_admin=is_admin,
            data={
                "subscription_id": subscription_id
            }
        )
    
    def unsubscribe_all(self, auth_token: Optional[str] = None, is_admin: bool = True) -> Dict[str, Any]:
        """
        Unsubscribe from all Realtime channels.
        
        Note: Supabase's Realtime API does not support server-side management of 
        websocket connections. For client applications, it's better to use 
        the client's native method: client.realtime.remove_all_channels()
        
        This method attempts to use the server API but will often return permission errors
        as the endpoints are not publicly accessible. It's provided for compatibility and
        diagnostic purposes only.
        
        Args:
            auth_token: Optional JWT token for authenticated requests
            is_admin: Whether to use the service role key (admin access)
            
        Returns:
            Success message or error details when API fails
        """
        response = {
            "status": "warning",
            "message": "Server-side channel management is not fully supported by Supabase Realtime API."
        }
        
        # Add recommendation for client-side approach
        response["recommendation"] = (
            "For client applications, use: await client.realtime.remove_all_channels() " +
            "instead of this server-side method."
        )
        
        # For RLS issues, add policy recommendations
        response["rls_info"] = (
            "Ensure your channel naming follows the required format for RLS: " +
            "'private-[schema]-[table]-[*|id]' and that proper RLS policies are in place."
        )
        
        # Try the server API but don't expect success
        try:
            api_response = self._make_request(
                method="POST",
                endpoint="/realtime/v1/unsubscribe_all",
                auth_token=auth_token,
                is_admin=is_admin,
                data={}
            )
            response["api_response"] = api_response
            response["status"] = "success"
            response["message"] = "Successfully unsubscribed from all channels using server API (unusual)."  
            return response  
        except Exception as e:
            # Expected behavior - API endpoint is usually restricted
            error_info = {
                "status": "error",
                "message": str(e)
            }
            
            # Add status code if available
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                error_info["status_code"] = e.response.status_code
                
                # Special handling for 403 errors - expected for this endpoint
                if e.response.status_code == 403:
                    # This is normal - update status to warning
                    response["error_details"] = "Permission denied (403) when accessing the unsubscribe_all endpoint. " +\
                                              "This is expected behavior as Supabase restricts server-side management of realtime channels."
                    response["sql_policy"] = """-- Recommended RLS policies for Supabase Realtime
-- Run these in your Supabase SQL Editor

-- Enable RLS on the realtime schema tables
ALTER TABLE realtime.messages ENABLE ROW LEVEL SECURITY;

-- Create policies for realtime messages
CREATE POLICY "Allow authenticated users to select from realtime messages" 
ON realtime.messages 
FOR SELECT 
TO authenticated 
USING (true);

CREATE POLICY "Allow authenticated users to insert into realtime messages" 
ON realtime.messages 
FOR INSERT 
TO authenticated 
WITH CHECK (true);

-- Allow use of presence features
CREATE POLICY "Allow authenticated users to use presence" 
ON realtime.presence 
FOR ALL
TO authenticated 
USING (true);
                    """
                    
            response["api_error"] = error_info
            return response
    
    def get_channels(self, auth_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve all subscribed channels.
        
        Note: When using Supabase Realtime with RLS, channels should follow the naming
        convention: 'private-[schema]-[table]-[*|id]' for proper authorization.
        Examples:
          - 'private-public-users-*' (all users table changes)
          - 'private-public-users-123' (specific user ID)
        
        This method attempts to access the /realtime/v1/channels endpoint which
        may require admin privileges. If you encounter 403 errors, consider using
        your Supabase client's realtime.channels property directly instead.
        
        Args:
            auth_token: Optional JWT token for authenticated requests
            
        Returns:
            Dict containing list of subscribed channels
        
        Raises:
            Exception: When the request fails and no fallback data is available
        """
        try:
            # First attempt: Use admin access to get channels via API endpoint
            return self._make_request(
                method="GET",
                endpoint="/realtime/v1/channels",
                auth_token=auth_token,
                is_admin=True  # Always use admin access for this endpoint
            )
        except Exception as e:
            # If this fails with a 403, it might be that the endpoint requires a specific format
            # or doesn't work with the current Supabase version
            error_msg = str(e).lower()
            if '403' in error_msg or 'forbidden' in error_msg or 'unauthorized' in error_msg:
                # Log the issue
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    "Could not access Realtime channels endpoint; " 
                    "this may be expected if your Supabase version doesn't support it. "
                    "Consider accessing client.realtime.channels directly instead."
                )
                # Return an empty channel list
                return {"channels": [], "error": "API endpoint unavailable - use client-side methods"}
            else:
                # For other errors, re-raise
                raise
    
    def broadcast_message(self, 
                        channel: str, 
                        payload: Dict[str, Any],
                        event: str = "broadcast",
                        auth_token: Optional[str] = None,
                        is_admin: bool = True) -> Dict[str, Any]:
        """
        Broadcast a message to a channel.
        
        Args:
            channel: Channel name
            payload: Message payload
            event: Event name (default: "broadcast")
            auth_token: Optional JWT token for authenticated requests
            is_admin: Whether to use the service role key (admin access)
            
        Returns:
            Response data
        """
        return self._make_request(
            method="POST",
            endpoint="/realtime/v1/broadcast",
            auth_token=auth_token,
            is_admin=is_admin,
            data={
                "channel": channel,
                "event": event,
                "payload": payload
            }
        )
