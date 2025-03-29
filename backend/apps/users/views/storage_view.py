from typing import Any, Dict, List, Optional, Union
import base64
from io import BytesIO
import os
import logging

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes, authentication_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from apps.authentication.authentication import SupabaseJWTAuthentication
from apps.supabase_home.storage import SupabaseStorageService


# Initialize the storage service
storage_service = SupabaseStorageService()


def _get_auth_token(request: Request) -> Optional[str]:
    """
    Extract the auth token from the request.
    
    Checks in the following order:
    1. request.auth.token (set by DRF authentication)
    2. Authorization header (for tests using APIClient)
    3. request.data.get('auth_token') (for POST requests)
    4. request.query_params.get('auth_token') (for GET requests)
    
    Returns:
        Optional[str]: The auth token if found, None otherwise
    """
    # Check if token is in request.auth
    if hasattr(request, "auth") and request.auth is not None and hasattr(request.auth, "token"):
        return request.auth.token
    
    # Check if token is in Authorization header (for tests)
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    
    # Check if token is in request data (for POST requests)
    if request.method in ["POST", "PUT", "PATCH"] and request.data.get("auth_token"):
        return request.data.get("auth_token")
    
    # Check if token is in query params (for GET/DELETE requests)
    if request.method in ["GET", "DELETE"] and request.query_params.get("auth_token"):
        return request.query_params.get("auth_token")
    
    return None


# Bucket Management
@api_view(["POST"])
@authentication_classes([SupabaseJWTAuthentication])
@permission_classes([IsAuthenticated])
def create_bucket(request: Request) -> Response:
    """
    Create a new storage bucket.
    
    Request body:
    - bucket_id: Bucket identifier (required)
    - public: Whether the bucket should be public (default: false)
    - file_size_limit: Maximum file size in bytes (optional)
    - allowed_mime_types: List of allowed MIME types (optional)
    - is_admin: Whether to use admin privileges (optional)
    - auth_token: Optional auth token to use instead of the request's auth token
    """
    # Get required parameters
    bucket_id = request.data.get("bucket_id")
    if not bucket_id:
        return Response(
            {"error": "Bucket ID is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Get optional parameters
    public = request.data.get("public", False)
    file_size_limit = request.data.get("file_size_limit")
    allowed_mime_types = request.data.get("allowed_mime_types")

    # Build the request data
    data = {
        "id": bucket_id,
        "public": public,
    }

    if file_size_limit:
        data["file_size_limit"] = file_size_limit

    if allowed_mime_types:
        data["allowed_mime_types"] = allowed_mime_types

    try:
        # Get auth token
        auth_token = _get_auth_token(request)

        # Check if admin access is requested - convert string to boolean
        is_admin = request.data.get("is_admin", "False")
        is_admin = is_admin.lower() == "true" if isinstance(is_admin, str) else bool(is_admin)

        bucket = storage_service.create_bucket(
            bucket_id=bucket_id,
            public=public,
            file_size_limit=file_size_limit,
            allowed_mime_types=allowed_mime_types,
            auth_token=auth_token,
            is_admin=is_admin,
        )
        return Response({"name": bucket["name"]}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response(
            {"error": f"Failed to create bucket: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@authentication_classes([SupabaseJWTAuthentication])
@permission_classes([IsAuthenticated])
def get_bucket(request: Request) -> Response:
    """
    Retrieve a bucket by ID.

    Query parameters:
    - bucket_id: Bucket identifier (required)
    - is_admin: Whether to use admin privileges (optional)
    - auth_token: Optional auth token to use instead of the request's auth token
    """
    bucket_id = request.query_params.get("bucket_id")

    if not bucket_id:
        return Response(
            {"error": "Bucket ID is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token
        auth_token = _get_auth_token(request)

        # Check if admin access is requested - convert string to boolean
        is_admin = request.query_params.get("is_admin", "False")
        is_admin = is_admin.lower() == "true" if isinstance(is_admin, str) else bool(is_admin)

        response = storage_service.get_bucket(
            bucket_id=bucket_id, auth_token=auth_token, is_admin=is_admin
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to get bucket: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@authentication_classes([SupabaseJWTAuthentication])
@permission_classes([IsAuthenticated])
def list_buckets(request: Request) -> Response:
    """
    List all storage buckets.
    
    Query parameters:
    - is_admin: Whether to use admin privileges (optional)
    - auth_token: Optional auth token to use instead of the request's auth token
    """
    try:
        # Get auth token
        auth_token = _get_auth_token(request)
        
        # Check if admin access is requested - convert string to boolean
        is_admin = request.query_params.get("is_admin", "False")
        is_admin = is_admin.lower() == "true" if isinstance(is_admin, str) else bool(is_admin)
        
        buckets = storage_service.list_buckets(auth_token=auth_token, is_admin=is_admin)
        return Response({"buckets": buckets}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to list buckets: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["PUT"])
@authentication_classes([SupabaseJWTAuthentication])
@permission_classes([IsAuthenticated])
def update_bucket(request: Request) -> Response:
    """
    Update a bucket.

    Request body:
    - bucket_id: Bucket identifier (required)
    - public: Whether the bucket is publicly accessible
    - file_size_limit: Optional file size limit in bytes
    - allowed_mime_types: Optional list of allowed MIME types
    - auth_token: Optional auth token to use instead of the request's auth token
    """
    bucket_id = request.data.get("bucket_id")
    public = request.data.get("public")
    file_size_limit = request.data.get("file_size_limit")
    allowed_mime_types = request.data.get("allowed_mime_types")

    if not bucket_id:
        return Response(
            {"error": "Bucket ID is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token
        auth_token = _get_auth_token(request)

        response = storage_service.update_bucket(
            bucket_id=bucket_id,
            public=public,
            file_size_limit=file_size_limit,
            allowed_mime_types=allowed_mime_types,
            auth_token=auth_token,
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to update bucket: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["DELETE"])
@authentication_classes([SupabaseJWTAuthentication])
@permission_classes([IsAuthenticated])
def delete_bucket(request: Request) -> Response:
    """
    Delete a bucket.

    Query parameters:
    - bucket_id: Bucket identifier (required)
    - auth_token: Optional auth token to use instead of the request's auth token
    """
    bucket_id = request.query_params.get("bucket_id")

    if not bucket_id:
        return Response(
            {"error": "Bucket ID is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token
        auth_token = _get_auth_token(request)

        response = storage_service.delete_bucket(
            bucket_id=bucket_id, auth_token=auth_token
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to delete bucket: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@authentication_classes([SupabaseJWTAuthentication])
@permission_classes([IsAuthenticated])
def empty_bucket(request: Request) -> Response:
    """
    Empty a bucket (delete all files).

    Request body:
    - bucket_id: Bucket identifier (required)
    - auth_token: Optional auth token to use instead of the request's auth token
    """
    bucket_id = request.data.get("bucket_id")

    if not bucket_id:
        return Response(
            {"error": "Bucket ID is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token
        auth_token = _get_auth_token(request)

        response = storage_service.empty_bucket(
            bucket_id=bucket_id, auth_token=auth_token
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to empty bucket: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# File Management
@api_view(["POST"])
@authentication_classes([SupabaseJWTAuthentication])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def upload_file(request: Request) -> Response:
    """
    Upload a file to a bucket.

    Request body (multipart/form-data):
    - bucket_id: Bucket identifier (required)
    - path: File path within the bucket (required)
    - file: File data (required)
    - content_type: MIME type of the file (optional)
    - auth_token: Optional auth token to use instead of the request's auth token

    OR

    Request body (application/json):
    - bucket_id: Bucket identifier (required)
    - path: File path within the bucket (required)
    - file_data: Base64-encoded file data (required)
    - content_type: MIME type of the file (optional)
    - auth_token: Optional auth token to use instead of the request's auth token
    """
    bucket_id = request.data.get("bucket_id")
    path = request.data.get("path")
    content_type = request.data.get("content_type")

    if not bucket_id or not path:
        return Response(
            {"error": "Bucket ID and path are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check if file is uploaded as multipart form or as base64 data
    file = request.FILES.get("file")
    file_data = request.data.get("file_data")

    if not file and not file_data:
        return Response(
            {"error": "File or file_data is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token
        auth_token = _get_auth_token(request)

        # Check if admin access is requested - convert string to boolean
        is_admin = request.data.get("is_admin", "False")
        is_admin = is_admin.lower() == "true" if isinstance(is_admin, str) else bool(is_admin)

        if file:
            # Handle multipart form upload
            file_content = file.read()
            if not content_type:
                content_type = file.content_type
        else:
            # Handle base64 encoded data
            try:
                file_content = base64.b64decode(file_data)
            except Exception:
                return Response(
                    {"error": "Invalid base64 data"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        response = storage_service.upload_file(
            bucket_id=bucket_id,
            path=path,
            file_data=file_content,
            content_type=content_type,
            auth_token=auth_token,
            is_admin=is_admin,
        )
        return Response(response, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response(
            {"error": f"Failed to upload file: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@authentication_classes([SupabaseJWTAuthentication])
@permission_classes([IsAuthenticated])
def download_file(request: Request) -> Response:
    """
    Download a file from a bucket.

    Query parameters:
    - bucket_id: Bucket identifier (required)
    - path: File path (required)
    - is_admin: Whether to use admin privileges (optional)
    - auth_token: Optional auth token to use instead of the request's auth token
    """
    # Get required parameters
    bucket_id = request.query_params.get("bucket_id")
    path = request.query_params.get("path")

    if not bucket_id:
        return Response(
            {"error": "Bucket ID is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not path:
        return Response(
            {"error": "Path is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token
        auth_token = _get_auth_token(request)

        # Check if admin access is requested - convert string to boolean
        is_admin = request.query_params.get("is_admin", "False")
        is_admin = is_admin.lower() == "true" if isinstance(is_admin, str) else bool(is_admin)

        # Get the file
        file_data, content_type = storage_service.download_file(
            bucket_id=bucket_id,
            path=path,
            auth_token=auth_token,
            is_admin=is_admin,
        )

        # Create a response with the raw file data
        from django.http import HttpResponse
        response = HttpResponse(file_data, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{os.path.basename(path)}"'
        return response
    except Exception as e:
        return Response(
            {"error": f"Failed to download file: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@authentication_classes([SupabaseJWTAuthentication])
@permission_classes([IsAuthenticated])
def list_files(request: Request) -> Response:
    """
    List files in a bucket.
    
    Required parameters:
    - bucket_id: The ID of the bucket to list files from
    
    Optional parameters:
    - path: Path prefix to filter files (default: "")
    - limit: Maximum number of files to return (default: 100)
    - offset: Offset for pagination (default: 0)
    - sort_by: Optional sorting parameters
    - is_admin: Whether to use service role key (admin access)
    - auth_token: Optional JWT token for authenticated requests
    
    Returns:
        Response with a list of files
    """
    logger = logging.getLogger("storage_view")
    
    # Extract parameters
    bucket_id = request.data.get("bucket_id")
    path = request.data.get("path", "")
    limit = request.data.get("limit", 100)
    offset = request.data.get("offset", 0)
    sort_by = request.data.get("sort_by")
    is_admin = request.data.get("is_admin", False)
    
    # Validate required parameters
    if not bucket_id:
        return Response(
            {"error": "bucket_id is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get auth token with enhanced logging
    auth_token = _get_auth_token(request)
    logger.info(f"Auth token available: {bool(auth_token)}")
    if auth_token:
        logger.info(f"Auth token first 10 chars: {auth_token[:10]}...")
    else:
        logger.warning("No auth token found in request")
        logger.debug(f"Request auth: {request.auth}")
        logger.debug(f"Request user: {request.user}")
        logger.debug(f"Request META: {request.META.get('HTTP_AUTHORIZATION', 'Not found')}")
    
    # Get storage service
    storage_service = SupabaseStorageService()
    
    try:
        # List files
        logger.info(f"Listing files in bucket {bucket_id} with path {path}")
        logger.info(f"Using admin access: {is_admin}")
        
        result = storage_service.list_files(
            bucket_id=bucket_id,
            path=path,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            auth_token=auth_token,
            is_admin=is_admin
        )
        
        return Response({"files": result}, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        return Response(
            {"error": f"Failed to list files: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@authentication_classes([SupabaseJWTAuthentication])
@permission_classes([IsAuthenticated])
def move_file(request: Request) -> Response:
    """
    Move a file to a new location.

    Request body:
    - bucket_id: Bucket identifier (required)
    - source_path: Current file path (required)
    - destination_path: New file path (required)
    - auth_token: Optional auth token to use instead of the request's auth token
    """
    bucket_id = request.data.get("bucket_id")
    source_path = request.data.get("source_path")
    destination_path = request.data.get("destination_path")

    if not bucket_id or not source_path or not destination_path:
        return Response(
            {"error": "Bucket ID, source path, and destination path are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token
        auth_token = _get_auth_token(request)

        response = storage_service.move_file(
            bucket_id=bucket_id,
            source_path=source_path,
            destination_path=destination_path,
            auth_token=auth_token,
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to move file: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@authentication_classes([SupabaseJWTAuthentication])
@permission_classes([IsAuthenticated])
def copy_file(request: Request) -> Response:
    """
    Copy a file to a new location.

    Request body:
    - bucket_id: Bucket identifier (required)
    - source_path: Source file path (required)
    - destination_path: Destination file path (required)
    - auth_token: Optional auth token to use instead of the request's auth token
    """
    bucket_id = request.data.get("bucket_id")
    source_path = request.data.get("source_path")
    destination_path = request.data.get("destination_path")

    if not bucket_id or not source_path or not destination_path:
        return Response(
            {"error": "Bucket ID, source path, and destination path are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token
        auth_token = _get_auth_token(request)

        response = storage_service.copy_file(
            bucket_id=bucket_id,
            source_path=source_path,
            destination_path=destination_path,
            auth_token=auth_token,
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to copy file: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@authentication_classes([SupabaseJWTAuthentication])
@permission_classes([IsAuthenticated])
def delete_file(request: Request) -> Response:
    """
    Delete files from a bucket.

    Args:
        request: Request object containing:
            bucket_id: Bucket identifier
            path: File path or list of file paths to delete
            is_admin: Whether to use admin privileges

    Returns:
        Success message
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Get parameters from request
        bucket_id = request.data.get('bucket_id')
        file_path = request.data.get('path')
        is_admin = request.data.get('is_admin', False)
        
        # Validate required parameters
        if not bucket_id:
            return Response({"error": "bucket_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not file_path:
            return Response({"error": "path is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get auth token from request
        auth_token = _get_auth_token(request)
        
        # Process file paths to ensure they're in the correct format
        file_paths = file_path if isinstance(file_path, list) else [file_path]
        
        # Get storage service
        storage_service = SupabaseStorageService()
        
        # Log the parameters being sent to the storage service
        logger.info(f"Deleting files from bucket {bucket_id}: {file_paths}")
        logger.info(f"Using auth_token: {bool(auth_token)}, is_admin: {is_admin}")
        
        # Make direct call to storage service with explicit parameters
        response = storage_service.delete_file(
            bucket_id=bucket_id, 
            paths=file_paths,  # Use our processed file_paths list
            auth_token=auth_token,
            is_admin=is_admin
        )
        
        # Verify the deletion was successful
        logger.info(f"Delete operation response: {response}")
        
        return Response({"message": "Files deleted successfully"}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error deleting files: {str(e)}")
        logger.exception("Detailed exception information:")
        return Response({"error": f"Failed to delete file(s): {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# URL Management
@api_view(["POST"])
@authentication_classes([SupabaseJWTAuthentication])
@permission_classes([IsAuthenticated])
def create_signed_url(request: Request) -> Response:
    """
    Create a signed URL for a file.

    Request body:
    - bucket_id: Bucket identifier (required)
    - path: File path (required)
    - expires_in: Expiration time in seconds (default: 60)
    - auth_token: Optional auth token to use instead of the request's auth token
    """
    bucket_id = request.data.get("bucket_id")
    path = request.data.get("path")
    expires_in = request.data.get("expires_in", 60)

    if not bucket_id or not path:
        return Response(
            {"error": "Bucket ID and path are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token
        auth_token = _get_auth_token(request)

        response = storage_service.create_signed_url(
            bucket_id=bucket_id, path=path, expires_in=expires_in, auth_token=auth_token
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to create signed URL: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@authentication_classes([SupabaseJWTAuthentication])
@permission_classes([IsAuthenticated])
def create_signed_urls(request: Request) -> Response:
    """
    Create signed URLs for multiple files.

    Request body:
    - bucket_id: Bucket identifier (required)
    - paths: List of file paths (required)
    - expires_in: Expiration time in seconds (default: 60)
    - auth_token: Optional auth token to use instead of the request's auth token
    """
    bucket_id = request.data.get("bucket_id")
    paths = request.data.get("paths")
    expires_in = request.data.get("expires_in", 60)

    if not bucket_id or not paths or not isinstance(paths, list):
        return Response(
            {"error": "Bucket ID and paths (as a list) are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token
        auth_token = _get_auth_token(request)

        response = storage_service.create_signed_urls(
            bucket_id=bucket_id,
            paths=paths,
            expires_in=expires_in,
            auth_token=auth_token,
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to create signed URLs: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@authentication_classes([SupabaseJWTAuthentication])
@permission_classes([IsAuthenticated])
def create_signed_upload_url(request: Request) -> Response:
    """
    Create a signed URL for uploading a file.

    Request body:
    - bucket_id: Bucket identifier (required)
    - path: File path (required)
    - auth_token: Optional auth token to use instead of the request's auth token
    """
    bucket_id = request.data.get("bucket_id")
    path = request.data.get("path")

    if not bucket_id or not path:
        return Response(
            {"error": "Bucket ID and path are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token
        auth_token = _get_auth_token(request)

        response = storage_service.create_signed_upload_url(
            bucket_id=bucket_id, path=path, auth_token=auth_token
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to create signed upload URL: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["PUT"])
@authentication_classes([SupabaseJWTAuthentication])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def upload_to_signed_url(request: Request) -> Response:
    """
    Upload a file to a signed URL.

    Request body (multipart/form-data):
    - signed_url: Signed URL for upload (required)
    - file: File data (required)
    - content_type: MIME type of the file (optional)
    - auth_token: Optional auth token to use instead of the request's auth token

    OR

    Request body (application/json):
    - signed_url: Signed URL for upload (required)
    - file_data: Base64-encoded file data (required)
    - content_type: MIME type of the file (optional)
    - auth_token: Optional auth token to use instead of the request's auth token
    """
    signed_url = request.data.get("signed_url")
    content_type = request.data.get("content_type")

    if not signed_url:
        return Response(
            {"error": "Signed URL is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check if file is uploaded as multipart form or as base64 data
    file = request.FILES.get("file")
    file_data = request.data.get("file_data")

    if not file and not file_data:
        return Response(
            {"error": "File or file_data is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token
        auth_token = _get_auth_token(request)

        if file:
            # Handle multipart form upload
            file_content = file.read()
            if not content_type:
                content_type = file.content_type
        else:
            # Handle base64 encoded data
            try:
                file_content = base64.b64decode(file_data)
            except Exception:
                return Response(
                    {"error": "Invalid base64 data"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        storage_service.upload_to_signed_url(
            signed_url=signed_url, 
            file_data=file_content, 
            content_type=content_type,
            auth_token=auth_token  # Pass the auth token to the service
        )
        return Response(
            {"message": "File uploaded successfully"}, status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to upload file to signed URL: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_public_url(request: Request) -> Response:
    """
    Get a public URL for a file in a public bucket.
    
    Query parameters:
    - bucket_id: Bucket identifier (required)
    - path: File path (required)
    
    Returns:
        Response with the public URL
    """
    bucket_id = request.query_params.get("bucket_id")
    path = request.query_params.get("path")
    
    if not bucket_id or not path:
        return Response(
            {"error": "bucket_id and path are required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        url = storage_service.get_public_url(bucket_id=bucket_id, path=path)
        return Response({"public_url": url}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to get public URL: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
