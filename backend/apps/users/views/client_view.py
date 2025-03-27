from typing import Any, Dict, List, Optional

from django.conf import settings
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

# Import the Supabase client
from apps.supabase_home.client import supabase


# Database views
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def execute_query(request: Request) -> Response:
    """
    Execute a database query using the Supabase client.

    Query parameters:
    - query: SQL query to execute
    - params: Optional parameters for the query
    """
    query = request.query_params.get("query")
    params = request.query_params.get("params", {})

    if not query:
        return Response(
            {"error": "Query parameter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get the database service and execute the query
        db_service = supabase.get_database_service()
        response = db_service.execute_query(query, params)
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to execute query: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Storage views
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def list_buckets(request: Request) -> Response:
    """
    List all storage buckets.
    """
    try:
        storage_service = supabase.get_storage_service()
        response = storage_service.list_buckets()
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to list buckets: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def create_bucket(request: Request) -> Response:
    """
    Create a new storage bucket.
    """
    bucket_name = request.data.get("bucket_name")
    bucket_options = request.data.get("options", {})

    if not bucket_name:
        return Response(
            {"error": "Bucket name is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        storage_service = supabase.get_storage_service()
        response = storage_service.create_bucket(bucket_name, bucket_options)
        return Response(response, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response(
            {"error": f"Failed to create bucket: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def list_objects(request: Request) -> Response:
    """
    List objects in a bucket.
    """
    bucket_name = request.query_params.get("bucket_name")
    path = request.query_params.get("path", "")

    if not bucket_name:
        return Response(
            {"error": "Bucket name is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        storage_service = supabase.get_storage_service()
        response = storage_service.list_objects(bucket_name, path)
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to list objects: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def upload_file(request: Request) -> Response:
    """
    Upload a file to a bucket.
    """
    bucket_name = request.data.get("bucket_name")
    file_path = request.data.get("file_path")
    file = request.FILES.get("file")

    if not bucket_name or not file_path or not file:
        return Response(
            {"error": "Bucket name, file path, and file are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        storage_service = supabase.get_storage_service()
        response = storage_service.upload(bucket_name, file_path, file)
        return Response(response, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response(
            {"error": f"Failed to upload file: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def delete_file(request: Request) -> Response:
    """
    Delete a file from a bucket.
    """
    bucket_name = request.data.get("bucket_name")
    file_path = request.data.get("file_path")

    if not bucket_name or not file_path:
        return Response(
            {"error": "Bucket name and file path are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        storage_service = supabase.get_storage_service()
        response = storage_service.delete(bucket_name, [file_path])
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to delete file: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Edge Functions views
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def invoke_edge_function(request: Request) -> Response:
    """
    Invoke an edge function.
    """
    function_name = request.data.get("function_name")
    invoke_options = request.data.get("options", {})

    if not function_name:
        return Response(
            {"error": "Function name is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        edge_functions_service = supabase.get_edge_functions_service()
        response = edge_functions_service.invoke(function_name, invoke_options)
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to invoke edge function: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Realtime views
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def subscribe_to_channel(request: Request) -> Response:
    """
    Subscribe to a realtime channel.
    This endpoint provides information on how to subscribe.
    Actual subscription should be handled on the client side.
    """
    channel_name = request.data.get("channel_name")

    if not channel_name:
        return Response(
            {"error": "Channel name is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # This is just informational - actual subscription happens client-side
        return Response(
            {
                "message": f"To subscribe to channel '{channel_name}', use the Supabase client in your frontend application.",
                "example": f"const channel = supabase.channel('{channel_name}').subscribe()",
            },
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to process subscription info: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
