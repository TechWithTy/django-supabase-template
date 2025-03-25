import json
from typing import Dict, Any, Callable, Optional, TypeVar, cast
from functools import wraps

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.users.models import UserProfile
from apps.credits.models import CreditTransaction

# Type variable for generic function
T = TypeVar('T')


def call_function_with_credits(func: Callable[[Request], Response], 
                              request: Request, 
                              credit_amount: int = 5) -> Response:
    """
    Utility function that calls a specific function with credit-based access control.
    
    Args:
        func: The function to call (must accept a Request object as its first parameter)
        request: The request object to pass to the function
        credit_amount: Number of credits required to execute the function (default: 5)
    
    Returns:
        The response from the function, with credit information added
    
    Example usage:
    ```python
    @api_view(["POST"])
    @permission_classes([IsAuthenticated])
    def my_api_endpoint(request):
        return call_function_with_credits(some_expensive_function, request, credit_amount=10)
    ```
    """
    # Only proceed if the user is authenticated
    if not request.user.is_authenticated:
        return Response(
            {"error": "Authentication required"},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Get the actual credit amount (allow admin override)
    actual_credit_amount = credit_amount
    if request.user.is_staff or request.user.is_superuser:
        # Allow admins to override the credit amount
        requested_amount = request.data.get("credit_amount")
        if requested_amount is not None:
            try:
                actual_credit_amount = int(requested_amount)
                if actual_credit_amount < 0:
                    return Response(
                        {"error": "Credit amount cannot be negative"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except (ValueError, TypeError):
                return Response(
                    {"error": "Credit amount must be a valid integer"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
    
    # Get the user's profile
    try:
        profile, created = UserProfile.objects.get_or_create(
            user=request.user, 
            defaults={"supabase_uid": request.user.username}
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to retrieve user profile: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    
    # Check if the user has enough credits (skip for admins if they set credits to 0)
    if actual_credit_amount > 0 and not profile.has_sufficient_credits(actual_credit_amount):
        return Response(
            {
                "error": "Insufficient credits",
                "required": actual_credit_amount,
                "available": profile.credits_balance,
                "message": f"This operation requires {actual_credit_amount} credits. You have {profile.credits_balance} credits available."
            },
            status=status.HTTP_402_PAYMENT_REQUIRED,
        )
    
    try:
        # Execute the function
        response = func(request)
        
        # Only deduct credits if the function executed successfully
        if actual_credit_amount > 0 and response.status_code < 400:
            # Deduct credits from the user's account
            profile.deduct_credits(actual_credit_amount)
            
            # Record the credit transaction
            CreditTransaction.objects.create(
                user=request.user,
                amount=-actual_credit_amount,
                balance_after=profile.credits_balance,
                description=f"Executed {func.__name__}",
                endpoint=request.path
            )
            
            # Add credit information to the response data
            if hasattr(response, 'data') and isinstance(response.data, dict):
                response.data['credits_used'] = actual_credit_amount
                response.data['credits_remaining'] = profile.credits_balance
        
        return response
        
    except Exception as e:
        return Response(
            {"error": f"Failed to execute function: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Example usage with a demo function
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def credit_based_function_demo(request: Request) -> Response:
    """
    Example endpoint showing how to use the call_function_with_credits utility.
    
    This function demonstrates how to wrap an existing function with credit-based access control.
    
    Request body:
    - parameters: Any parameters needed by the wrapped function
    - credit_amount: Optional override for the credit cost (admin only)
    
    Returns:
    - The output of the wrapped function with credit information added
    """
    def demo_function(req: Request) -> Response:
        # This could be any function that processes data and returns a Response
        parameters = req.data.get("parameters", {})
        
        # Process the parameters and return a response
        result = {
            "message": "Function executed successfully",
            "processed_parameters": parameters
        }
        
        return Response(result, status=status.HTTP_200_OK)
    
    # Call the function with credit-based access control
    return call_function_with_credits(demo_function, request, credit_amount=3)
