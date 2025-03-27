from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .client import supabase
import logging

logger = logging.getLogger(" apps.supabase_home")


@csrf_exempt
@require_http_methods(["GET"])
def example_supabase_view(request):
    """
    Example view demonstrating how to use the Supabase client in Django.

    This view shows how to:
    1. Use the Supabase database service to fetch data
    2. Handle errors properly
    3. Return JSON responses

    URL: /api/supabase/example/
    Method: GET

    Returns:
        JsonResponse: JSON response with data or error message
    """
    try:
        # Get the database service from the Supabase client
        db_service = supabase.get_database_service()

        # Example: Fetch data from a table (replace 'your_table' with an actual table name)
        # For demonstration purposes only
        table_name = "example_table"  # Replace with your actual table name

        try:
            # Try to fetch data from the table
            data = db_service.fetch_data(table=table_name, limit=10)
            return JsonResponse(
                {
                    "success": True,
                    "data": data,
                    "message": f"Successfully fetched data from {table_name}",
                }
            )
        except Exception as e:
            # If the table doesn't exist or there's another error, log it
            logger.warning(f"Error fetching data: {str(e)}")

            # Return a fallback response showing the Supabase connection is working
            return JsonResponse(
                {
                    "success": True,
                    "data": None,
                    "message": "Supabase client is configured correctly, but could not fetch data. "
                    "This is expected if the example table does not exist.",
                }
            )

    except Exception as e:
        # Log any unexpected errors
        logger.exception(f"Unexpected error in example_supabase_view: {str(e)}")

        # Return an error response
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
                "message": "An error occurred while connecting to Supabase.",
            },
            status=500,
        )


@csrf_exempt
@require_http_methods(["GET"])
def supabase_health_check(request):
    """
    Health check endpoint for Supabase connection.

    This view attempts to initialize the Supabase client and reports
    whether the connection is working properly.

    URL: /api/supabase/health/
    Method: GET

    Returns:
        JsonResponse: JSON response with connection status
    """
    try:
        # Get the raw Supabase client to check if it's initialized
        raw_client = supabase.get_raw_client()

        # If we get here, the client was initialized successfully
        return JsonResponse(
            {
                "status": "ok",
                "message": "Supabase client is configured correctly",
                "supabase_url": raw_client.supabase_url,  # Safe to show the URL
            }
        )
    except Exception as e:
        # Log the error
        logger.exception(f"Supabase health check failed: {str(e)}")

        # Return an error response
        return JsonResponse(
            {
                "status": "error",
                "message": "Supabase client configuration error",
                "error": str(e),
            },
            status=500,
        )
