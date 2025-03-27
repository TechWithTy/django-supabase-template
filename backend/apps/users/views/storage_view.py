from typing import Any, Dict, List, Optional, Union
import base64
from io import BytesIO

from django.conf import settings
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.request import Request
from rest_framework.response import Response

# Import the SupabaseStorageService directly
from apps.supabase_home.storage import SupabaseStorageService

# Initialize the storage service
storage_service = SupabaseStorageService()


# Bucket Management
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def create_bucket(request: Request) -> Response:
    """
    Create a new storage bucket.

    Request body:
    - bucket_id: Bucket identifier (required)
    - public: Whether the bucket is publicly accessible (default: false)
    - file_size_limit: Optional file size limit in bytes
    - allowed_mime_types: Optional list of allowed MIME types
    """
    bucket_id = request.data.get("bucket_id")
    public = request.data.get("public", False)
    file_size_limit = request.data.get("file_size_limit")
    allowed_mime_types = request.data.get("allowed_mime_types")

    if not bucket_id:
        return Response(
            {"error": "Bucket ID is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

        response = storage_service.create_bucket(
            bucket_id=bucket_id,
            public=public,
            file_size_limit=file_size_limit,
            allowed_mime_types=allowed_mime_types,
            auth_token=auth_token,
        )
        return Response(response, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response(
            {"error": f"Failed to create bucket: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_bucket(request: Request) -> Response:
    """
    Retrieve a bucket by ID.

    Query parameters:
    - bucket_id: Bucket identifier (required)
    """
    bucket_id = request.query_params.get("bucket_id")

    if not bucket_id:
        return Response(
            {"error": "Bucket ID is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

        response = storage_service.get_bucket(
            bucket_id=bucket_id, auth_token=auth_token
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to get bucket: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def list_buckets(request: Request) -> Response:
    """
    List all buckets.
    """
    try:
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

        response = storage_service.list_buckets(auth_token=auth_token)
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to list buckets: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["PUT"])
@permission_classes([permissions.IsAuthenticated])
def update_bucket(request: Request) -> Response:
    """
    Update a bucket.

    Request body:
    - bucket_id: Bucket identifier (required)
    - public: Whether the bucket is publicly accessible
    - file_size_limit: Optional file size limit in bytes
    - allowed_mime_types: Optional list of allowed MIME types
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
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

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
@permission_classes([permissions.IsAuthenticated])
def delete_bucket(request: Request) -> Response:
    """
    Delete a bucket.

    Query parameters:
    - bucket_id: Bucket identifier (required)
    """
    bucket_id = request.query_params.get("bucket_id")

    if not bucket_id:
        return Response(
            {"error": "Bucket ID is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

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
@permission_classes([permissions.IsAuthenticated])
def empty_bucket(request: Request) -> Response:
    """
    Empty a bucket (delete all files).

    Request body:
    - bucket_id: Bucket identifier (required)
    """
    bucket_id = request.data.get("bucket_id")

    if not bucket_id:
        return Response(
            {"error": "Bucket ID is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

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
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def upload_file(request: Request) -> Response:
    """
    Upload a file to a bucket.

    Request body (multipart/form-data):
    - bucket_id: Bucket identifier (required)
    - path: File path within the bucket (required)
    - file: File data (required)
    - content_type: MIME type of the file (optional)

    OR

    Request body (application/json):
    - bucket_id: Bucket identifier (required)
    - path: File path within the bucket (required)
    - file_data: Base64-encoded file data (required)
    - content_type: MIME type of the file (optional)
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
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

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
        )
        return Response(response, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response(
            {"error": f"Failed to upload file: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def download_file(request: Request) -> Response:
    """
    Download a file from a bucket.

    Query parameters:
    - bucket_id: Bucket identifier (required)
    - path: File path within the bucket (required)
    """
    bucket_id = request.query_params.get("bucket_id")
    path = request.query_params.get("path")

    if not bucket_id or not path:
        return Response(
            {"error": "Bucket ID and path are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

        file_content = storage_service.download_file(
            bucket_id=bucket_id, path=path, auth_token=auth_token
        )

        # Try to determine content type from file extension
        import mimetypes

        content_type, _ = mimetypes.guess_type(path)
        if not content_type:
            content_type = "application/octet-stream"

        return Response(
            file_content,
            status=status.HTTP_200_OK,
            headers={
                "Content-Type": content_type,
                "Content-Disposition": f"attachment; filename={path.split('/')[-1]}",
            },
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to download file: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def list_files(request: Request) -> Response:
    """
    List files in a bucket.

    Request body:
    - bucket_id: Bucket identifier (required)
    - path: Path prefix to filter files (default: "")
    - limit: Maximum number of files to return (default: 100)
    - offset: Offset for pagination (default: 0)
    - sort_by: Optional sorting parameters
    """
    bucket_id = request.data.get("bucket_id")
    path = request.data.get("path", "")
    limit = request.data.get("limit", 100)
    offset = request.data.get("offset", 0)
    sort_by = request.data.get("sort_by")

    if not bucket_id:
        return Response(
            {"error": "Bucket ID is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

        response = storage_service.list_files(
            bucket_id=bucket_id,
            path=path,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            auth_token=auth_token,
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to list files: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def move_file(request: Request) -> Response:
    """
    Move a file to a new location.

    Request body:
    - bucket_id: Bucket identifier (required)
    - source_path: Current file path (required)
    - destination_path: New file path (required)
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
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

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
@permission_classes([permissions.IsAuthenticated])
def copy_file(request: Request) -> Response:
    """
    Copy a file to a new location.

    Request body:
    - bucket_id: Bucket identifier (required)
    - source_path: Source file path (required)
    - destination_path: Destination file path (required)
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
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

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


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def delete_file(request: Request) -> Response:
    """
    Delete files from a bucket.

    Query parameters (for single file):
    - bucket_id: Bucket identifier (required)
    - path: File path (required if paths not provided in body)

    OR

    Request body (for multiple files):
    - bucket_id: Bucket identifier (required)
    - paths: List of file paths to delete (required if path not provided in query)
    """
    # Check if bucket_id and path are provided in query params (single file delete)
    bucket_id = request.query_params.get("bucket_id") or request.data.get("bucket_id")
    path = request.query_params.get("path")
    paths = request.data.get("paths")

    if not bucket_id:
        return Response(
            {"error": "Bucket ID is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not path and not paths:
        return Response(
            {"error": "Either path or paths must be provided"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # If path is provided in query params, use it
    if path:
        paths = path

    try:
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

        response = storage_service.delete_file(
            bucket_id=bucket_id, paths=paths, auth_token=auth_token
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to delete file(s): {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# URL Management
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def create_signed_url(request: Request) -> Response:
    """
    Create a signed URL for a file.

    Request body:
    - bucket_id: Bucket identifier (required)
    - path: File path (required)
    - expires_in: Expiration time in seconds (default: 60)
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
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

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
@permission_classes([permissions.IsAuthenticated])
def create_signed_urls(request: Request) -> Response:
    """
    Create signed URLs for multiple files.

    Request body:
    - bucket_id: Bucket identifier (required)
    - paths: List of file paths (required)
    - expires_in: Expiration time in seconds (default: 60)
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
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

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
@permission_classes([permissions.IsAuthenticated])
def create_signed_upload_url(request: Request) -> Response:
    """
    Create a signed URL for uploading a file.

    Request body:
    - bucket_id: Bucket identifier (required)
    - path: File path (required)
    """
    bucket_id = request.data.get("bucket_id")
    path = request.data.get("path")

    if not bucket_id or not path:
        return Response(
            {"error": "Bucket ID and path are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

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
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def upload_to_signed_url(request: Request) -> Response:
    """
    Upload a file to a signed URL.

    Request body (multipart/form-data):
    - signed_url: Signed URL for upload (required)
    - file: File data (required)
    - content_type: MIME type of the file (optional)

    OR

    Request body (application/json):
    - signed_url: Signed URL for upload (required)
    - file_data: Base64-encoded file data (required)
    - content_type: MIME type of the file (optional)
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
            signed_url=signed_url, file_data=file_content, content_type=content_type
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
@permission_classes([permissions.AllowAny])
def get_public_url(request: Request) -> Response:
    """
    Get the public URL for a file in a public bucket.

    Query parameters:
    - bucket_id: Bucket identifier (required)
    - path: File path (required)
    """
    bucket_id = request.query_params.get("bucket_id")
    path = request.query_params.get("path")

    if not bucket_id or not path:
        return Response(
            {"error": "Bucket ID and path are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        public_url = storage_service.get_public_url(bucket_id=bucket_id, path=path)
        return Response({"url": public_url}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to get public URL: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
