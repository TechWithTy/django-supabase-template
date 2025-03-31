from django.conf import settings
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response
from django.core.cache import cache
import hashlib
import logging
import re

# Import the Supabase client
from apps.supabase_home.client import supabase

# Import Redis cache utilities
from apps.caching.utils.redis_cache import get_cached_result

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
        logger.error(f"Failed to get Supabase URL: {str(e)}")
        return Response(
            {"error": "Failed to get Supabase URL"},
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
        logger.error(f"Failed to get Supabase anon key: {str(e)}")
        return Response(
            {"error": "Failed to get Supabase anon key"},
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
        logger.error(f"Failed to get Supabase client info: {str(e)}")
        return Response(
            {"error": "Failed to get Supabase client info"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Database views
@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])  # Restrict to admin users only
def execute_query(request: Request) -> Response:
    """
    Execute a database query using the Supabase client.
    
    SECURITY NOTE: This endpoint is restricted to admin users only and should
    be used with caution. Consider disabling in production environments.

    Query parameters:
    - query: SQL query to execute (must be a SELECT query only)
    - params: Optional parameters for the query
    """
    query = request.query_params.get("query")
    params = request.query_params.get("params", {})

    if not query:
        return Response(
            {"error": "Query parameter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    # Security check: Only allow SELECT queries
    if not query.strip().lower().startswith('select'):
        logger.warning(f"Attempted unsafe query execution: {query}")
        return Response(
            {"error": "Only SELECT queries are allowed"},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        # Get the database service and execute the query
        db_service = supabase.get_database_service()
        response = db_service.execute_query(query, params)
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        error_message = str(e)
        logger.error(f"Query execution error: {error_message}")
        
        # Don't expose detailed error messages
        return Response(
            {"error": "Failed to execute query"},
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
        error_message = str(e)
        logger.error(f"Failed to list buckets: {error_message}")
        return Response(
            {"error": "Failed to list storage buckets"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def create_bucket(request: Request) -> Response:
    """Create a new storage bucket."""
    bucket_id = request.data.get("bucket_id")
    public = request.data.get("public", False)
    file_size_limit = request.data.get("file_size_limit")
    allowed_mime_types = request.data.get("allowed_mime_types")

    # Validate inputs
    if not bucket_id:
        return Response(
            {"error": "Bucket ID is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate bucket name to prevent injection attacks
    if not re.match(r'^[a-zA-Z0-9_-]+$', bucket_id):
        return Response(
            {"error": "Invalid bucket ID format"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        storage_service = supabase.get_storage_service()
        response = storage_service.create_bucket(
            bucket_id=bucket_id,
            public=public,
            file_size_limit=file_size_limit,
            allowed_mime_types=allowed_mime_types,
        )
        return Response(response, status=status.HTTP_201_CREATED)
    except Exception as e:
        error_message = str(e)
        logger.error(f"Failed to create bucket: {error_message}")
        return Response(
            {"error": f"Failed to create storage bucket: {error_message}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def upload_file(request: Request) -> Response:
    """Upload a file to a storage bucket."""
    bucket_name = request.data.get("bucket_name")
    file_path = request.data.get("path")
    file_content = request.data.get("content")

    # Validate inputs
    if not bucket_name:
        return Response(
            {"error": "Bucket name is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate bucket name to prevent injection attacks
    if not re.match(r'^[a-zA-Z0-9_-]+$', bucket_name):
        return Response(
            {"error": "Invalid bucket name format"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not file_path:
        return Response(
            {"error": "File path is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if file_content is None:
        return Response(
            {"error": "File content is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Upload the file
        supabase.storage.from_(bucket_name).upload(
            file_path, file_content, {"content-type": "application/octet-stream"}
        )

        # Invalidate cache entries related to this bucket
        cache_pattern = f"storage:list:{bucket_name}:*"
        cache_keys = cache.keys(cache_pattern)
        if cache_keys:
            cache.delete_many(cache_keys)

        return Response(
            {"message": f"File '{file_path}' uploaded successfully"},
            status=status.HTTP_201_CREATED,
        )
    except Exception as e:
        logger.error("Error uploading file: %s", str(e))
        return Response(
            {"error": f"Failed to upload file: {str(e)}"},
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
        
    # Validate bucket name (alphanumeric, hyphens, underscores only)
    if not re.match(r'^[a-zA-Z0-9_-]+$', bucket_name):
        return Response(
            {"error": "Invalid bucket name format"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Generate a cache key based on bucket name and path
        # Use SHA-256 for secure hashing of the path
        cache_key = f"storage:list:{bucket_name}:{hashlib.sha256(path.encode()).hexdigest()}"
        
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
        else:
            return Response(
                {"error": "Failed to list objects in storage bucket"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def delete_file(request: Request) -> Response:
    """Delete a file from a storage bucket."""
    bucket_name = request.data.get("bucket_name")
    file_path = request.data.get("path")

    # Validate inputs
    if not bucket_name:
        return Response(
            {"error": "Bucket name is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate bucket name to prevent injection attacks
    if not re.match(r'^[a-zA-Z0-9_-]+$', bucket_name):
        return Response(
            {"error": "Invalid bucket name format"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not file_path:
        return Response(
            {"error": "File path is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Delete the file
        supabase.storage.from_(bucket_name).remove([file_path])

        # Invalidate cache entries related to this bucket
        cache_pattern = f"storage:list:{bucket_name}:*"
        cache_keys = cache.keys(cache_pattern)
        if cache_keys:
            cache.delete_many(cache_keys)

        return Response(
            {"message": f"File '{file_path}' deleted successfully"},
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        logger.error("Error deleting file: %s", str(e))
        return Response(
            {"error": f"Failed to delete file: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def create_directory(request: Request) -> Response:
    """Create a directory inside a storage bucket."""
    bucket_name = request.data.get("bucket_name")
    path = request.data.get("path")

    # Validate inputs
    if not bucket_name:
        return Response(
            {"error": "Bucket name is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate bucket name to prevent injection attacks
    if not re.match(r'^[a-zA-Z0-9_-]+$', bucket_name):
        return Response(
            {"error": "Invalid bucket name format"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not path:
        return Response(
            {"error": "Path is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Create an empty file to represent the directory
        file_path = f"{path.rstrip('/')}/.keep"
        
        # Upload an empty file to the specified path
        supabase.storage.from_(bucket_name).upload(
            file_path, b"", {"content-type": "text/plain"}
        )

        return Response(
            {"message": f"Directory '{path}' created successfully"},
            status=status.HTTP_201_CREATED,
        )
    except Exception as e:
        logger.error("Error creating directory: %s", str(e))
        return Response(
            {"error": f"Failed to create directory: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def delete_directory(request: Request) -> Response:
    """Delete a directory and all its contents from a storage bucket."""
    bucket_name = request.data.get("bucket_name")
    path = request.data.get("path")

    # Validate inputs
    if not bucket_name:
        return Response(
            {"error": "Bucket name is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate bucket name to prevent injection attacks
    if not re.match(r'^[a-zA-Z0-9_-]+$', bucket_name):
        return Response(
            {"error": "Invalid bucket name format"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not path:
        return Response(
            {"error": "Path is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # List all files in the directory
        list_response = supabase.storage.from_(bucket_name).list(path)
        file_paths = [f"{path}/{item['name']}" for item in list_response]

        # Delete each file in the directory
        for file_path in file_paths:
            supabase.storage.from_(bucket_name).remove([file_path])

        # Additionally, try to remove any .keep file that might represent the directory
        try:
            supabase.storage.from_(bucket_name).remove([f"{path.rstrip('/')}/.keep"])
        except Exception:
            # Ignore errors if .keep file doesn't exist
            pass

        return Response(
            {"message": f"Directory '{path}' deleted successfully"},
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        logger.error("Error deleting directory: %s", str(e))
        return Response(
            {"error": f"Failed to delete directory: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Edge Functions views
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def invoke_edge_function(request: Request) -> Response:
    """Invoke an edge function."""
    function_name = request.data.get("function_name")
    function_params = request.data.get("params", {})

    # Validate required fields
    if not function_name:
        return Response(
            {"error": "Function name is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate function name to prevent injection
    if not re.match(r'^[a-zA-Z0-9_-]+$', function_name):
        return Response(
            {"error": "Invalid function name format"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Invoke the edge function
        function_result = supabase.functions.invoke(function_name, function_params)

        return Response(function_result, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error("Error invoking edge function: %s", str(e))
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
