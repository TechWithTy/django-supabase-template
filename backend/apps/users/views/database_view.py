from typing import Any, Dict, List, Optional

from django.conf import settings
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

# Import the SupabaseDatabaseService directly
from apps.supabase_home.database import SupabaseDatabaseService

# Initialize the database service
db_service = SupabaseDatabaseService()


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

        response = db_service.fetch_data(
            table=table,
            auth_token=auth_token,
            select=select,
            filters=filters if filters else None,
            order=order,
            limit=limit,
            offset=offset,
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to fetch data: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def insert_data(request: Request) -> Response:
    """
    Insert data into a table.

    Request body:
    - table: Table name (required)
    - data: Data to insert (single record or list of records) (required)
    - upsert: Whether to upsert (update on conflict) (default: false)
    """
    table = request.data.get("table")
    data = request.data.get("data")
    upsert = request.data.get("upsert", False)

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
            table=table, data=data, auth_token=auth_token, upsert=upsert
        )
        return Response(response, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response(
            {"error": f"Failed to insert data: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["PATCH"])
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
            table=table, data=data, filters=filters, auth_token=auth_token
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to update data: {str(e)}"},
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
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to delete data: {str(e)}"},
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
