from typing import Any, Dict, List, Optional

from django.conf import settings
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response
from django.core.cache import cache
import hashlib
import logging

# Import the Supabase client
from apps.supabase_home.client import supabase

# Import Redis cache utilities
from apps.caching.utils.redis_cache import (
    cache_result,
    get_cached_result,
    get_or_set_cache,
    invalidate_cache
)

logger = logging.getLogger(__name__)

# Client info endpoints
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_supabase_url(request: Request) -> Response:
    """
    Get the Supabase URL for client-side usage.
    """
    try:
        return Response(
            {"supabase_url": settings.SUPABASE_URL},
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to get Supabase URL: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_supabase_anon_key(request: Request) -> Response:
    """
    Get the Supabase anonymous key for client-side usage.
    """
    try:
        return Response(
            {"supabase_anon_key": settings.SUPABASE_ANON_KEY},
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to get Supabase anon key: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_supabase_client_info(request: Request) -> Response:
    """
    Get the Supabase client info (URL and anon key) for client-side usage.
    """
    try:
        return Response(
            {
                "supabase_url": settings.SUPABASE_URL,
                "supabase_anon_key": settings.SUPABASE_ANON_KEY,
            },
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to get Supabase client info: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


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
        # Generate a cache key based on bucket name and path
        cache_key = f"storage:list:{bucket_name}:{hashlib.md5(path.encode()).hexdigest()}"
        
        # Try to get data from cache first
        cached_data = get_cached_result(cache_key)
        
        if cached_data is not None:
            logger.debug(f"Cache hit for bucket listing: {bucket_name}")
            return Response(cached_data, status=status.HTTP_200_OK)
        
        # Cache miss - fetch data from storage service
        logger.debug(f"Cache miss for bucket listing: {bucket_name}")
        storage_service = supabase.get_storage_service()
        response = storage_service.list_objects(bucket_name, path)
        
        # Cache the result for 5 minutes (300 seconds)
        # Storage listings don't change very frequently, but we don't want to cache too long
        # in case files are added or removed
        cache.set(cache_key, response, timeout=300)
        
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        error_message = str(e)
        logger.error(f"Storage listing error: {error_message}")
        
        # Handle specific error types
        if "not found" in error_message.lower() or "does not exist" in error_message.lower():
            return Response(
                {"error": f"Bucket '{bucket_name}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        elif "permission denied" in error_message.lower() or "not authorized" in error_message.lower():
            return Response(
                {"error": "You don't have permission to access this bucket"},
                status=status.HTTP_403_FORBIDDEN,
            )
        else:
            return Response(
                {"error": f"Failed to list objects: {error_message}"},
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
    file_data = request.data.get("file_data")

    if not bucket_name or not file_path or not file_data:
        return Response(
            {"error": "Bucket name, file path, and file data are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        storage_service = supabase.get_storage_service()
        response = storage_service.upload_file(bucket_name, file_path, file_data)
        
        # Invalidate cache for this bucket's listings
        # Extract the directory path from the file path to invalidate the correct cache entries
        directory_path = "/".join(file_path.split("/")[:-1])
        
        # Generate cache key patterns for invalidation
        # We need to invalidate both the exact directory and parent directories
        cache_patterns = [
            f"storage:list:{bucket_name}:*",  # All listings for this bucket
        ]
        
        # Find and delete all matching cache keys
        for pattern in cache_patterns:
            keys_to_delete = cache.keys(pattern)
            if keys_to_delete:
                logger.debug(f"Invalidating {len(keys_to_delete)} cache keys after file upload to bucket: {bucket_name}")
                cache.delete_many(keys_to_delete)
        
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        error_message = str(e)
        logger.error(f"File upload error: {error_message}")
        
        # Handle specific error types
        if "not found" in error_message.lower() or "does not exist" in error_message.lower():
            return Response(
                {"error": f"Bucket '{bucket_name}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        elif "permission denied" in error_message.lower() or "not authorized" in error_message.lower():
            return Response(
                {"error": "You don't have permission to upload to this bucket"},
                status=status.HTTP_403_FORBIDDEN,
            )
        elif "size limit" in error_message.lower() or "too large" in error_message.lower():
            return Response(
                {"error": "File exceeds size limit"},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )
        else:
            return Response(
                {"error": f"Failed to upload file: {error_message}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def delete_file(request: Request) -> Response:
    """
    Delete a file from a bucket.
    """
    bucket_name = request.query_params.get("bucket_name")
    file_path = request.query_params.get("file_path")

    if not bucket_name or not file_path:
        return Response(
            {"error": "Bucket name and file path are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        storage_service = supabase.get_storage_service()
        response = storage_service.delete_file(bucket_name, file_path)
        
        # Invalidate cache for this bucket's listings
        # Extract the directory path from the file path to invalidate the correct cache entries
        directory_path = "/".join(file_path.split("/")[:-1])
        
        # Generate cache key patterns for invalidation
        cache_patterns = [
            f"storage:list:{bucket_name}:*",  # All listings for this bucket
        ]
        
        # Find and delete all matching cache keys
        for pattern in cache_patterns:
            keys_to_delete = cache.keys(pattern)
            if keys_to_delete:
                logger.debug(f"Invalidating {len(keys_to_delete)} cache keys after file deletion from bucket: {bucket_name}")
                cache.delete_many(keys_to_delete)
        
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        error_message = str(e)
        logger.error(f"File deletion error: {error_message}")
        
        # Handle specific error types
        if "not found" in error_message.lower() or "does not exist" in error_message.lower():
            return Response(
                {"error": f"Bucket '{bucket_name}' or file '{file_path}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        elif "permission denied" in error_message.lower() or "not authorized" in error_message.lower():
            return Response(
                {"error": "You don't have permission to delete from this bucket"},
                status=status.HTTP_403_FORBIDDEN,
            )
        else:
            return Response(
                {"error": f"Failed to delete file: {error_message}"},
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
