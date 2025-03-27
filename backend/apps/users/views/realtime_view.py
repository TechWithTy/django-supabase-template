from typing import Any, Dict, List, Optional

from django.conf import settings
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

# Import the SupabaseRealtimeService directly
from apps.supabase_home.realtime import SupabaseRealtimeService

# Initialize the realtime service
realtime_service = SupabaseRealtimeService()


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def subscribe_to_channel(request: Request) -> Response:
    """
    Subscribe to a Realtime channel.

    Request body:
    - channel: Channel name (required)
    - event: Event to subscribe to (default: "*" for all events)
    """
    channel = request.data.get("channel")
    event = request.data.get("event", "*")

    if not channel:
        return Response(
            {"error": "Channel name is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

        response = realtime_service.subscribe_to_channel(
            channel=channel, event=event, auth_token=auth_token
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to subscribe to channel: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def unsubscribe_from_channel(request: Request) -> Response:
    """
    Unsubscribe from a Realtime channel.

    Request body:
    - subscription_id: Subscription ID (required)
    """
    subscription_id = request.data.get("subscription_id")

    if not subscription_id:
        return Response(
            {"error": "Subscription ID is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

        response = realtime_service.unsubscribe_from_channel(
            subscription_id=subscription_id, auth_token=auth_token
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to unsubscribe from channel: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def unsubscribe_all(request: Request) -> Response:
    """
    Unsubscribe from all Realtime channels.
    """
    try:
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

        response = realtime_service.unsubscribe_all(auth_token=auth_token)
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to unsubscribe from all channels: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_channels(request: Request) -> Response:
    """
    Retrieve all subscribed channels.
    """
    try:
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

        response = realtime_service.get_channels(auth_token=auth_token)
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to retrieve channels: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def broadcast_message(request: Request) -> Response:
    """
    Broadcast a message to a channel.

    Request body:
    - channel: Channel name (required)
    - event: Event name (required)
    - payload: Message payload (required)
    """
    channel = request.data.get("channel")
    event = request.data.get("event")
    payload = request.data.get("payload")

    if not channel or not event or not payload:
        return Response(
            {"error": "Channel, event, and payload are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not isinstance(payload, dict):
        return Response(
            {"error": "Payload must be a JSON object"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

        response = realtime_service.broadcast_message(
            channel=channel, event=event, payload=payload, auth_token=auth_token
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to broadcast message: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
