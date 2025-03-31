from typing import Any, Dict, List, Optional, Union, BinaryIO, Tuple
import os
import requests

from ._service import SupabaseService


class SupabaseStorageService(SupabaseService):
    """
    Service for interacting with Supabase Storage API.

    This class provides methods for managing buckets and files
    in Supabase Storage.
    """

    def create_bucket(
        self,
        bucket_id: str,
        public: bool = False,
        file_size_limit: Optional[int] = None,
        allowed_mime_types: Optional[List[str]] = None,
        auth_token: Optional[str] = None,
        is_admin: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a new storage bucket.

        Args:
            bucket_id: Bucket identifier
            public: Whether the bucket is publicly accessible
            file_size_limit: Optional file size limit in bytes
            allowed_mime_types: Optional list of allowed MIME types
            auth_token: Optional JWT token for authenticated requests
            is_admin: Whether to use service role key (admin access)

        Returns:
            Bucket data
        """
        data = {"name": bucket_id, "public": public}

        if file_size_limit is not None:
            data["file_size_limit"] = file_size_limit

        if allowed_mime_types is not None:
            data["allowed_mime_types"] = allowed_mime_types

        # Ensure we're using admin privileges for bucket creation
        # This is required to bypass row-level security policies
        # Bucket creation typically requires admin privileges in Supabase
        if not is_admin:
            is_admin = True

        # Ensure data is always a valid JSON body
        data = data or {}

        return self._make_request(
            method="POST",
            endpoint="/storage/v1/bucket",
            auth_token=auth_token,
            is_admin=is_admin,
            data=data,
        )

    def get_bucket(
        self, bucket_id: str, auth_token: Optional[str] = None, is_admin: bool = False
    ) -> Dict[str, Any]:
        """
        Retrieve a bucket by ID.

        Args:
            bucket_id: Bucket identifier
            auth_token: Optional JWT token for authenticated requests
            is_admin: Whether to use admin privileges

        Returns:
            Bucket data
        """
        return self._make_request(
            method="GET",
            endpoint="/storage/v1/bucket/" + bucket_id,
            auth_token=auth_token,
            is_admin=is_admin,
        )

    def list_buckets(
        self, auth_token: Optional[str] = None, is_admin: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List all buckets.

        Args:
            auth_token: Optional JWT token for authenticated requests
            is_admin: Whether to use service role key (admin access)

        Returns:
            List of buckets
        """
        return self._make_request(
            method="GET",
            endpoint="/storage/v1/bucket",
            auth_token=auth_token,
            is_admin=is_admin,
        )

    def update_bucket(
        self,
        bucket_id: str,
        public: Optional[bool] = None,
        file_size_limit: Optional[int] = None,
        allowed_mime_types: Optional[List[str]] = None,
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update a bucket.

        Args:
            bucket_id: Bucket identifier
            public: Whether the bucket is publicly accessible
            file_size_limit: Optional file size limit in bytes
            allowed_mime_types: Optional list of allowed MIME types
            auth_token: Optional JWT token for authenticated requests

        Returns:
            Updated bucket data
        """
        data = {}

        if public is not None:
            data["public"] = public

        if file_size_limit is not None:
            data["file_size_limit"] = file_size_limit

        if allowed_mime_types is not None:
            data["allowed_mime_types"] = allowed_mime_types

        return self._make_request(
            method="PUT",
            endpoint="/storage/v1/bucket/" + bucket_id,
            auth_token=auth_token,
            data=data,
        )

    def delete_bucket(
        self, bucket_id: str, auth_token: Optional[str] = None, is_admin: bool = False
    ) -> Dict[str, Any]:
        """
        Delete a bucket.

        Args:
            bucket_id: Bucket identifier
            auth_token: Optional JWT token for authenticated requests
            is_admin: Whether to use service role key (admin access)

        Returns:
            Success message
        """
        return self._make_request(
            method="DELETE",
            endpoint="/storage/v1/bucket/" + bucket_id,
            auth_token=auth_token,
            is_admin=is_admin,
            data={},
        )

    def empty_bucket(
        self, bucket_id: str, auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Empty a bucket (delete all files).

        Args:
            bucket_id: Bucket identifier
            auth_token: Optional JWT token for authenticated requests

        Returns:
            Success message
        """
        return self._make_request(
            method="POST",
            endpoint="/storage/v1/bucket/" + bucket_id + "/empty",
            auth_token=auth_token,
        )

    def upload_file(
        self,
        bucket_id: str,
        path: str,
        file_data: Union[bytes, BinaryIO],
        content_type: Optional[str] = None,
        auth_token: Optional[str] = None,
        is_admin: bool = False,
    ) -> Dict[str, Any]:
        """
        Upload a file to a bucket.

        Args:
            bucket_id: Bucket identifier
            path: File path within the bucket
            file_data: File data as bytes or file-like object
            content_type: Optional content type
            auth_token: Optional JWT token for authenticated requests
            is_admin: Whether to use service role key (admin access)

        Returns:
            File data
        """
        url = f"{self.base_url}/storage/v1/object/{bucket_id}/{path}"

        # Get headers with authentication
        headers = self._get_headers(auth_token, is_admin)
        
        # Set content type based on provided value or file extension
        if content_type:
            headers["Content-Type"] = content_type
        else:
            # Try to guess content type from file extension
            _, ext = os.path.splitext(path)
            if ext.lower() in [".jpg", ".jpeg"]:
                headers["Content-Type"] = "image/jpeg"
            elif ext.lower() == ".png":
                headers["Content-Type"] = "image/png"
            elif ext.lower() == ".pdf":
                headers["Content-Type"] = "application/pdf"
            elif ext.lower() in [".txt", ".md"]:
                headers["Content-Type"] = "text/plain"
            elif ext.lower() == ".json":
                headers["Content-Type"] = "application/json"
            else:
                headers["Content-Type"] = "application/octet-stream"

        try:
            # For file uploads, we need to use requests directly instead of _make_request
            # because we're not sending JSON data
            import logging
            logger = logging.getLogger("apps.supabase_home")
            logger.info(f"Uploading file to {bucket_id}/{path} with content type: {headers.get('Content-Type')}")
            logger.info(f"Headers: {headers}")
            
            response = requests.post(url, headers=headers, data=file_data, timeout=30)
            
            # Log the response status and headers
            logger.info(f"Upload response status: {response.status_code}")
            logger.info(f"Upload response headers: {response.headers}")
            
            # Log the response content for debugging
            if response.status_code >= 400:
                logger.error(f"Upload error response: {response.text}")
            
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            # Log the error and re-raise with more context
            import logging
            logger = logging.getLogger("apps.supabase_home")
            logger.error(f"Error uploading file to {bucket_id}/{path}: {str(e)}")
            
            # Log request details
            logger.error(f"Request URL: {url}")
            logger.error(f"Request headers: {headers}")
            
            from ._service import SupabaseAPIError
            error_details = {}
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_details = e.response.json()
                    logger.error(f"Error response JSON: {error_details}")
                except ValueError:
                    error_details = {"status": e.response.status_code, "text": e.response.text}
                    logger.error(f"Error response text: {e.response.text}")
            
            raise SupabaseAPIError(
                message=f"Error uploading file: {str(e)}",
                status_code=getattr(e.response, "status_code", None) if hasattr(e, "response") else None,
                details=error_details
            )

    def download_file(
        self, bucket_id: str, path: str, auth_token: Optional[str] = None, is_admin: bool = False
    ) -> Tuple[bytes, str]:
        """
        Download a file from a bucket.

        Args:
            bucket_id: Bucket identifier
            path: File path
            auth_token: Optional JWT token for authenticated requests
            is_admin: Whether to use admin privileges

        Returns:
            Tuple of (file_content, content_type)
        """
        try:
            url = f"{self.base_url}/storage/v1/object/{bucket_id}/{path}"
            headers = self._get_headers(auth_token, is_admin)
            
            # For file downloads, we need to use requests directly instead of _make_request
            # because we want the raw response content
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Get content type from response headers or guess from file extension
            content_type = response.headers.get('Content-Type')
            if not content_type:
                import mimetypes
                content_type, _ = mimetypes.guess_type(path)
                if not content_type:
                    content_type = "application/octet-stream"
            
            return response.content, content_type
        except requests.exceptions.RequestException as e:
            # Log the error and re-raise with more context
            import logging
            logger = logging.getLogger("apps.supabase_home")
            logger.error(f"Error downloading file from {bucket_id}/{path}: {str(e)}")
            
            from ._service import SupabaseAPIError
            error_details = {}
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_details = e.response.json()
                except ValueError:
                    error_details = {"status": e.response.status_code, "text": e.response.text}
            
            raise SupabaseAPIError(
                message=f"Error downloading file: {str(e)}",
                status_code=getattr(e.response, "status_code", None) if hasattr(e, "response") else None,
                details=error_details
            )

    def list_files(
        self,
        bucket_id: str,
        path: str = "",
        limit: int = 100,
        offset: int = 0,
        sort_by: Optional[Dict[str, str]] = None,
        auth_token: Optional[str] = None,
        is_admin: bool = False,
    ) -> Dict[str, Any]:
        """
        List files in a bucket.

        Args:
            bucket_id: Bucket identifier
            path: Path prefix to filter files
            limit: Maximum number of files to return
            offset: Offset for pagination
            sort_by: Optional sorting parameters
            auth_token: Optional JWT token for authenticated requests
            is_admin: Whether to use service role key (admin access)

        Returns:
            List of files
        """
        import logging
        logger = logging.getLogger("apps.supabase_home")
        logger.info(f"Listing files in bucket {bucket_id} with path prefix: {path}")
        logger.info(f"Using admin access: {is_admin}")
        
        params = {"prefix": path, "limit": limit, "offset": offset}
        logger.info(f"Request params: {params}")

        if sort_by:
            params["sort_by"] = sort_by

        try:
            result = self._make_request(
                method="POST",
                endpoint="/storage/v1/object/list/" + bucket_id,
                auth_token=auth_token,
                is_admin=is_admin,
                data=params,
            )
            logger.info(f"Successfully listed files in bucket {bucket_id}")
            return result
        except Exception as e:
            logger.error(f"Error listing files in bucket {bucket_id}: {str(e)}")
            # Check if we need to try a different endpoint or method
            logger.info("Trying alternative endpoint for listing files")
            try:
                # Try GET method instead of POST
                result = self._make_request(
                    method="GET",
                    endpoint="/storage/v1/object/list/" + bucket_id,
                    auth_token=auth_token,
                    is_admin=is_admin,
                    params=params,  # Use params instead of data for GET request
                )
                logger.info("Successfully listed files using alternative endpoint")
                return result
            except Exception as alt_e:
                logger.error(f"Alternative endpoint also failed: {str(alt_e)}")
                raise

    def move_file(
        self,
        bucket_id: str,
        source_path: str,
        destination_path: str,
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Move a file to a new location.

        Args:
            bucket_id: Bucket identifier
            source_path: Current file path
            destination_path: New file path
            auth_token: Optional JWT token for authenticated requests

        Returns:
            Success message
        """
        return self._make_request(
            method="POST",
            endpoint="/storage/v1/object/move",
            auth_token=auth_token,
            data={
                "bucketId": bucket_id,
                "sourceKey": source_path,
                "destinationKey": destination_path,
            },
        )

    def copy_file(
        self,
        bucket_id: str,
        source_path: str,
        destination_path: str,
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Copy a file to a new location.

        Args:
            bucket_id: Bucket identifier
            source_path: Source file path
            destination_path: Destination file path
            auth_token: Optional JWT token for authenticated requests

        Returns:
            Success message
        """
        return self._make_request(
            method="POST",
            endpoint="/storage/v1/object/copy",
            auth_token=auth_token,
            data={
                "bucketId": bucket_id,
                "sourceKey": source_path,
                "destinationKey": destination_path,
            },
        )

    def delete_file(
        self,
        bucket_id: str,
        paths: Union[str, List[str]] = None,
        path: str = None,
        auth_token: Optional[str] = None,
        is_admin: bool = False,
    ) -> Dict[str, Any]:
        """
        Delete files from a bucket.

        Args:
            bucket_id: Bucket identifier
            paths: File path or list of file paths to delete
            path: Alternative parameter name for a single file path
            auth_token: Optional JWT token for authenticated requests
            is_admin: Whether to use admin privileges

        Returns:
            Success message
        """
        import logging
        logger = logging.getLogger("apps.supabase_home.storage")
        logger.info(f"Delete file called with bucket_id: {bucket_id}, paths: {paths}, path: {path}")
        logger.info(f"Auth token available: {bool(auth_token)}, is_admin: {is_admin}")
        
        # Handle both 'path' and 'paths' parameters for backward compatibility
        if path is not None and paths is None:
            paths = path
            logger.info(f"Using path parameter: {path}")
            
        if isinstance(paths, str):
            paths = [paths]
            logger.info(f"Converted string path to list: {paths}")

        # According to Supabase docs, the API expects a specific format
        # The key must be exactly 'prefixes' and it must be a list of strings
        request_data = {"prefixes": paths}
        logger.info(f"Making request with data: {request_data}")

        try:
            # Try individual file deletion first if there's only one file
            if len(paths) == 1 and paths[0]:
                single_path = paths[0]
                logger.info(f"Attempting single file deletion for: {single_path}")
                try:
                    # Use DELETE method for single file deletion
                    result = self._make_request(
                        method="DELETE",
                        endpoint=f"/storage/v1/object/{bucket_id}/{single_path.lstrip('/')}",
                        auth_token=auth_token,
                        is_admin=is_admin
                    )
                    logger.info(f"Single file deletion successful: {result}")
                    return result
                except Exception as single_delete_error:
                    logger.warning(f"Single file deletion failed, trying batch delete: {str(single_delete_error)}")
            
            # Try batch deletion as fallback or for multiple files
            logger.info("Attempting batch deletion")
            result = self._make_request(
                method="POST",
                endpoint=f"/storage/v1/bucket/{bucket_id}/remove",  # Corrected endpoint for batch deletion
                auth_token=auth_token,
                is_admin=is_admin,
                data=request_data,
            )
            logger.info(f"Batch deletion successful: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in delete_file: {str(e)}")
            logger.exception("Detailed exception information:")
            raise

    def create_signed_url(
        self,
        bucket_id: str,
        path: str,
        expires_in: int = 60,
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a signed URL for a file.

        Args:
            bucket_id: Bucket identifier
            path: File path
            expires_in: Expiration time in seconds
            auth_token: Optional JWT token for authenticated requests

        Returns:
            Signed URL data
        """
        return self._make_request(
            method="POST",
            endpoint="/storage/v1/object/sign/" + bucket_id + "/" + path,
            auth_token=auth_token,
            data={"expiresIn": expires_in},
        )

    def create_signed_urls(
        self,
        bucket_id: str,
        paths: List[str],
        expires_in: int = 60,
        auth_token: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Create signed URLs for multiple files.

        Args:
            bucket_id: Bucket identifier
            paths: List of file paths
            expires_in: Expiration time in seconds
            auth_token: Optional JWT token for authenticated requests

        Returns:
            List of signed URL data
        """
        return self._make_request(
            method="POST",
            endpoint="/storage/v1/object/sign/" + bucket_id,
            auth_token=auth_token,
            data={"expiresIn": expires_in, "paths": paths},
        )

    def create_signed_upload_url(
        self, bucket_id: str, path: str, auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a signed URL for uploading a file.

        Args:
            bucket_id: Bucket identifier
            path: File path
            auth_token: Optional JWT token for authenticated requests

        Returns:
            Signed upload URL data
        """
        return self._make_request(
            method="POST",
            endpoint="/storage/v1/object/upload/sign/" + bucket_id + "/" + path,
            auth_token=auth_token,
        )

    def upload_to_signed_url(
        self,
        signed_url: str,
        file_data: Union[bytes, BinaryIO],
        content_type: Optional[str] = None,
    ) -> None:
        """
        Upload a file to a signed URL.

        Args:
            signed_url: Signed URL for upload
            file_data: File data as bytes or file-like object
            content_type: MIME type of the file

        Returns:
            None
        """
        headers = {}
        if content_type:
            headers["Content-Type"] = content_type

        import requests

        response = requests.put(signed_url, headers=headers, data=file_data, timeout=30)  # Add 30-second timeout for security
        response.raise_for_status()

    def get_public_url(self, bucket_id: str, path: str, auth_token: Optional[str] = None, is_admin: bool = False) -> str:
        """
        Get a public URL for a file in a public bucket.

        Args:
            bucket_id: Bucket identifier
            path: File path
            auth_token: Optional JWT token for authenticated requests
            is_admin: Whether to use admin privileges

        Returns:
            Public URL
        """
        # Check if the bucket exists and is public
        try:
            bucket = self.get_bucket(bucket_id, auth_token=auth_token, is_admin=is_admin)
            if not bucket.get("public", False):
                raise ValueError(f"Bucket {bucket_id} is not public")
        except Exception as e:
            # If we can't verify the bucket is public, we'll still try to generate the URL
            # but log a warning
            import logging
            logger = logging.getLogger("apps.supabase_home")
            logger.warning(f"Could not verify bucket {bucket_id} is public: {str(e)}")

        return f"{self.base_url}/storage/v1/object/public/{bucket_id}/{path}"
