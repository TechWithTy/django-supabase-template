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
        
        Args:
            auth_token: Optional JWT token for authenticated requests
            is_admin: Whether to use the service role key (admin access)
            
        Returns:
            Success message
        """
        return self._make_request(
            method="POST",
            endpoint="/realtime/v1/unsubscribe_all",
            auth_token=auth_token,
            is_admin=is_admin
        )
    
    def get_channels(self, auth_token: Optional[str] = None, is_admin: bool = True) -> Dict[str, Any]:
        """
        Retrieve all subscribed channels.
        
        Args:
            auth_token: Optional JWT token for authenticated requests
            is_admin: Whether to use the service role key (admin access)
            
        Returns:
            Dict containing list of subscribed channels
        """
        return self._make_request(
            method="GET",
            endpoint="/realtime/v1/channels",
            auth_token=auth_token,
            is_admin=is_admin
        )
    
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
