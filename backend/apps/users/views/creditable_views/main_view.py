import subprocess
import os
import json
from typing import Dict, Any, Optional

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.users.models import UserProfile
from apps.credits.models import CreditTransaction


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def execute_main_script(request: Request) -> Response:
    """
    Execute the main.py script in the root directory with credit-based access control.
    
    This endpoint requires a specific number of credits per execution.
    Credits are deducted from the user's account before the script is run.
    
    Request body:
    - parameters: Dictionary of parameters to pass to the script (optional)
    - credit_amount: Optional override for the credit cost (admin only)
    
    Returns:
    - The output of the script execution along with credit information
    """
    # Define the default credit cost for this operation
    DEFAULT_CREDITS = 5
    
    # Get credit amount from request or use default
    credit_amount = DEFAULT_CREDITS
    if request.user.is_staff or request.user.is_superuser:
        # Allow admins to override the credit amount
        requested_amount = request.data.get("credit_amount")
        if requested_amount is not None:
            try:
                credit_amount = int(requested_amount)
                if credit_amount < 0:
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
    if credit_amount > 0 and not profile.has_sufficient_credits(credit_amount):
        return Response(
            {
                "error": "Insufficient credits",
                "required": credit_amount,
                "available": profile.credits_balance,
                "message": f"This operation requires {credit_amount} credits. You have {profile.credits_balance} credits available."
            },
            status=status.HTTP_402_PAYMENT_REQUIRED,
        )
    
    # Get parameters from the request
    parameters = request.data.get("parameters", {})
    
    try:
        # Construct the path to main.py in the root directory
        main_script_path = os.path.join(settings.BASE_DIR.parent, "main.py")
        
        # Check if the script exists
        if not os.path.exists(main_script_path):
            return Response(
                {"error": "Script not found. This template requires a main.py file in the root directory."},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        # Prepare the command to run the script
        command = ["python", main_script_path]
        
        # Add parameters as command line arguments
        for key, value in parameters.items():
            command.append(f"--{key}={value}")
        
        # Run the script and capture output
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,  # Don't raise an exception on non-zero exit
        )
        
        # Only deduct credits if the amount is greater than 0
        if credit_amount > 0:
            # Deduct credits from the user's account
            profile.deduct_credits(credit_amount)
            
            # Record the credit transaction
            CreditTransaction.objects.create(
                user=request.user,
                amount=-credit_amount,
                balance_after=profile.credits_balance,
                description="Executed main.py script",
                endpoint=request.path
            )
        
        # Parse the output
        response_data = _prepare_script_response(result, credit_amount, profile.credits_balance)
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {"error": f"Failed to execute script: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def _prepare_script_response(result: subprocess.CompletedProcess, 
                             credits_used: int, 
                             credits_remaining: int) -> Dict[str, Any]:
    """
    Prepare the response data from the script execution result.
    
    Attempts to parse JSON output if available and includes credit information.
    """
    response_data = {
        "success": result.returncode == 0,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "credits_used": credits_used,
        "credits_remaining": credits_remaining,
    }
    
    # Try to parse stdout as JSON if it looks like JSON
    if result.stdout.strip().startswith("{") and result.stdout.strip().endswith("}"):
        try:
            response_data["result"] = json.loads(result.stdout)
        except json.JSONDecodeError:
            # If it's not valid JSON, just use the raw output
            pass
    
    return response_data
