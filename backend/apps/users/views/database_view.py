from typing import Any, Dict, List, Optional

from django.conf import settings
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response
from django.core.cache import cache
import hashlib
import logging

# Import the SupabaseDatabaseService directly
from apps.supabase_home.database import SupabaseDatabaseService

# Import Redis cache utilities
from apps.caching.utils.redis_cache import (
    cache_result,
    get_cached_result,
    get_or_set_cache,
    invalidate_cache
)

# Initialize the database service
db_service = SupabaseDatabaseService()

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def fetch_data(request: Request) -> Response:
    """
    Fetch data from a table with optional filtering, ordering, and pagination.

    Query parameters:
    - table: Table name (required)
    - select: Columns to select (default: "*")
    - order: Optional order by clause
    - limit: Optional limit of rows to return
    - offset: Optional offset for pagination
    - Any additional parameters will be treated as filters
    """
    table = request.query_params.get("table")
    if not table:
        return Response(
            {"error": "Table parameter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Extract standard parameters
    select = request.query_params.get("select", "*")
    order = request.query_params.get("order")

    # Extract pagination parameters
    try:
        limit = (
            int(request.query_params.get("limit"))
            if request.query_params.get("limit")
            else None
        )
    except ValueError:
        return Response(
            {"error": "Limit must be an integer"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        offset = (
            int(request.query_params.get("offset"))
            if request.query_params.get("offset")
            else None
        )
    except ValueError:
        return Response(
            {"error": "Offset must be an integer"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Build filters from remaining query parameters
    filters = {}
    for key, value in request.query_params.items():
        if key not in ["table", "select", "order", "limit", "offset"]:
            filters[key] = value

    try:
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )
        
        # Generate a cache key based on the query parameters
        # Include all query parameters in the cache key to ensure uniqueness
        cache_key_parts = [
            f"table:{table}",
            f"select:{select}",
            f"order:{order or 'none'}",
            f"limit:{limit or 'none'}",
            f"offset:{offset or 'none'}",
        ]
        
        # Add filters to cache key
        for key, value in sorted(filters.items()):
            cache_key_parts.append(f"{key}:{value}")
            
        # Add user-specific part to the cache key if authenticated
        # This ensures users only see their own cached data
        if auth_token:
            # Use a hash of the token for security
            token_hash = hashlib.md5(auth_token.encode()).hexdigest()
            cache_key_parts.append(f"user:{token_hash}")
            
        # Join all parts and hash the result to keep the key length manageable
        cache_key_string = "|".join(cache_key_parts)
        cache_key = f"db_query:{hashlib.md5(cache_key_string.encode()).hexdigest()}"
        
        # Try to get data from cache first
        cached_data = get_cached_result(cache_key)
        
        if cached_data is not None:
            logger.debug(f"Cache hit for database query: {table}")
            return Response(cached_data, status=status.HTTP_200_OK)
            
        # Cache miss - fetch data from the database
        logger.debug(f"Cache miss for database query: {table}")
        response = db_service.fetch_data(
            table=table,
            auth_token=auth_token,
            select=select,
            filters=filters if filters else None,
            order=order,
            limit=limit,
            offset=offset,
        )
        
        # Cache the result
        # Use different cache timeouts based on the table and query type
        cache_timeout = 300  # Default: 5 minutes
        
        # Adjust timeout based on table type and query characteristics
        if table.lower() in ['logs', 'audit_logs', 'events']:
            # Short cache for frequently changing data
            cache_timeout = 60  # 1 minute
        elif table.lower() in ['settings', 'configurations', 'metadata']:
            # Longer cache for relatively static data
            cache_timeout = 1800  # 30 minutes
        elif limit == 1 and len(filters) > 0:
            # Single record lookups with filters (likely detail views)
            cache_timeout = 600  # 10 minutes
            
        # Don't cache empty results for as long
        if not response or (isinstance(response, list) and len(response) == 0):
            cache_timeout = 60  # 1 minute for empty results
            
        # Cache the response
        cache.set(cache_key, response, timeout=cache_timeout)
        
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        error_message = str(e)
        logger.error(f"Database query error: {error_message}")
        
        # Handle specific error types with appropriate status codes
        if "permission denied" in error_message.lower() or "not authorized" in error_message.lower():
            return Response(
                {"error": "You don't have permission to access this data"},
                status=status.HTTP_403_FORBIDDEN,
            )
        elif "not found" in error_message.lower() or "does not exist" in error_message.lower():
            return Response(
                {"error": f"Table '{table}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        else:
            return Response(
                {"error": f"Failed to fetch data: {error_message}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def insert_data(request: Request) -> Response:
    """
    Insert data into a table.

    Request body:
    - table: Table name (required)
    - data: Data to insert (required)
    """
    table = request.data.get("table")
    data = request.data.get("data")

    if not table:
        return Response(
            {"error": "Table parameter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not data:
        return Response(
            {"error": "Data parameter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

        response = db_service.insert_data(
            table=table,
            auth_token=auth_token,
            data=data,
        )
        
        # Invalidate cache for this table
        # This ensures that subsequent fetch_data calls will get fresh data
        cache_pattern = f"db_query:*"
        keys_to_delete = []
        
        # Find all cache keys that might contain data for this table
        for key in cache.keys(cache_pattern):
            # Check if this key is for the table being modified
            # We could be more specific, but this approach ensures we don't miss any keys
            # that might contain data for this table
            keys_to_delete.append(key)
        
        # Delete all matching cache keys
        if keys_to_delete:
            logger.debug(f"Invalidating {len(keys_to_delete)} cache keys for table: {table}")
            cache.delete_many(keys_to_delete)
        
        return Response(response, status=status.HTTP_201_CREATED)
    except Exception as e:
        error_message = str(e)
        logger.error(f"Database insert error: {error_message}")
        
        # Handle specific error types
        if "permission denied" in error_message.lower() or "not authorized" in error_message.lower():
            return Response(
                {"error": "You don't have permission to insert data into this table"},
                status=status.HTTP_403_FORBIDDEN,
            )
        elif "not found" in error_message.lower() or "does not exist" in error_message.lower():
            return Response(
                {"error": f"Table '{table}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        elif "duplicate key" in error_message.lower() or "unique constraint" in error_message.lower():
            return Response(
                {"error": "This record already exists (duplicate key violation)"},
                status=status.HTTP_409_CONFLICT,
            )
        else:
            return Response(
                {"error": f"Failed to insert data: {error_message}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def update_data(request: Request) -> Response:
    """
    Update data in a table.

    Request body:
    - table: Table name (required)
    - data: Data to update (required)
    - filters: Filters to identify rows to update (required)
    """
    table = request.data.get("table")
    data = request.data.get("data")
    filters = request.data.get("filters")

    if not table:
        return Response(
            {"error": "Table parameter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not data:
        return Response(
            {"error": "Data parameter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not filters:
        return Response(
            {"error": "Filters parameter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

        response = db_service.update_data(
            table=table,
            auth_token=auth_token,
            data=data,
            filters=filters,
        )
        
        # Invalidate cache for this table
        # We need to be more aggressive with cache invalidation on updates
        # since we don't know exactly which records were affected
        cache_pattern = f"db_query:*"
        keys_to_delete = []
        
        # Find all cache keys that might contain data for this table
        for key in cache.keys(cache_pattern):
            keys_to_delete.append(key)
        
        # Delete all matching cache keys
        if keys_to_delete:
            logger.debug(f"Invalidating {len(keys_to_delete)} cache keys after update to table: {table}")
            cache.delete_many(keys_to_delete)
        
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        error_message = str(e)
        logger.error(f"Database update error: {error_message}")
        
        # Handle specific error types
        if "permission denied" in error_message.lower() or "not authorized" in error_message.lower():
            return Response(
                {"error": "You don't have permission to update data in this table"},
                status=status.HTTP_403_FORBIDDEN,
            )
        elif "not found" in error_message.lower() or "does not exist" in error_message.lower():
            return Response(
                {"error": f"Table '{table}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        else:
            return Response(
                {"error": f"Failed to update data: {error_message}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def upsert_data(request: Request) -> Response:
    """
    Upsert data in a table (insert or update).

    Request body:
    - table: Table name (required)
    - data: Data to upsert (required)
    """
    table = request.data.get("table")
    data = request.data.get("data")

    if not table:
        return Response(
            {"error": "Table parameter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not data:
        return Response(
            {"error": "Data parameter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

        response = db_service.upsert_data(table=table, data=data, auth_token=auth_token)
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to upsert data: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def delete_data(request: Request) -> Response:
    """
    Delete data from a table.

    Request body:
    - table: Table name (required)
    - filters: Filters to identify rows to delete (required)
    """
    table = request.data.get("table")
    filters = request.data.get("filters")

    if not table:
        return Response(
            {"error": "Table parameter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not filters:
        return Response(
            {"error": "Filters parameter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

        response = db_service.delete_data(
            table=table, filters=filters, auth_token=auth_token
        )
        
        # Invalidate cache for this table
        # For deletes, we need to invalidate all cache entries that might contain the deleted data
        cache_pattern = f"db_query:*"
        keys_to_delete = []
        
        # Find all cache keys that might contain data for this table
        for key in cache.keys(cache_pattern):
            keys_to_delete.append(key)
        
        # Delete all matching cache keys
        if keys_to_delete:
            logger.debug(f"Invalidating {len(keys_to_delete)} cache keys after delete from table: {table}")
            cache.delete_many(keys_to_delete)
        
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        error_message = str(e)
        logger.error(f"Database delete error: {error_message}")
        
        # Handle specific error types
        if "permission denied" in error_message.lower() or "not authorized" in error_message.lower():
            return Response(
                {"error": "You don't have permission to delete data from this table"},
                status=status.HTTP_403_FORBIDDEN,
            )
        elif "not found" in error_message.lower() or "does not exist" in error_message.lower():
            return Response(
                {"error": f"Table '{table}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        elif "foreign key constraint" in error_message.lower():
            return Response(
                {"error": "Cannot delete this record because it is referenced by other records"},
                status=status.HTTP_409_CONFLICT,
            )
        else:
            return Response(
                {"error": f"Failed to delete data: {error_message}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def call_function(request: Request) -> Response:
    """
    Call a PostgreSQL function.

    Request body:
    - function_name: Function name (required)
    - params: Function parameters (optional)
    """
    function_name = request.data.get("function_name")
    params = request.data.get("params")

    if not function_name:
        return Response(
            {"error": "Function name parameter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get auth token if available
        auth_token = (
            request.auth.token
            if hasattr(request, "auth") and hasattr(request.auth, "token")
            else None
        )

        response = db_service.call_function(
            function_name=function_name, params=params, auth_token=auth_token
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to call function: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
