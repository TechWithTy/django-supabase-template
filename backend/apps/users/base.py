from typing import Any, Dict
import subprocess
import os
import json

from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

# Import the SupabaseAuthService directly
from apps.supabase.auth import SupabaseAuthService
from apps.credits.models import CreditTransaction

from .models import UserProfile
from .serializers import UserSerializer, UserProfileSerializer

# Initialize the Supabase Auth Service
auth_service = SupabaseAuthService()


class IsAdminOrSelf(permissions.BasePermission):
    """
    Custom permission to allow users to access only their own resources
    or admins to access any resource.
    """

    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        # Allow admins to access any resource
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Allow users to access only their own resources
        if isinstance(obj, User):
            return obj == request.user
        if isinstance(obj, UserProfile):
            return obj.user == request.user

        return False


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing users.

    This viewset provides CRUD operations for users, with appropriate
    permissions and additional endpoints for managing user-specific data.
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrSelf]

    def get_queryset(self):
        """
        Filter the queryset based on user permissions.
        """
        user = self.request.user

        # Admins can see all users
        if user.is_staff or user.is_superuser:
            return User.objects.all()

        # Regular users can only see themselves
        return User.objects.filter(id=user.id)

    @action(detail=False, methods=["get"])
    def me(self, request: Request) -> Response:
        """
        Get the current user's information.
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def add_credits(self, request: Request, pk=None) -> Response:
        """
        Add credits to a user's account.

        Only admins can add credits to any user. Users can't add credits to themselves.
        """
        user = self.get_object()
        amount = request.data.get("amount", 0)

        try:
            amount = int(amount)
            if amount <= 0:
                return Response(
                    {"error": "Amount must be a positive integer"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except (ValueError, TypeError):
            return Response(
                {"error": "Amount must be a valid integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Only admins can add credits
        if not request.user.is_staff and not request.user.is_superuser:
            return Response(
                {"error": "Only administrators can add credits"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Add credits to the user's profile
        try:
            profile, created = UserProfile.objects.get_or_create(
                user=user, defaults={"supabase_uid": user.username}
            )
            profile.add_credits(amount)

            return Response(
                {
                    "message": f"Added {amount} credits to {user.username}'s account",
                    "new_balance": profile.credits_balance,
                }
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to add credits: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    def supabase_users(self, request: Request) -> Response:
        """
        Get a list of users from Supabase.

        Only admins can access this endpoint.
        """
        # Only admins can list Supabase users
        if not request.user.is_staff and not request.user.is_superuser:
            return Response(
                {"error": "Only administrators can list Supabase users"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            # Use the SupabaseAuthService to list users
            response = auth_service.list_users()
            return Response(response, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve Supabase users: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def run_main_script(request: Request) -> Response:
    """
    Run the main.py script in the root directory.
    
    This endpoint requires a specific number of credits per execution.
    The credits are deducted from the user's account before the script is run.
    
    Request body:
    - parameters: Dictionary of parameters to pass to the script (optional)
    
    Returns:
    - The output of the script execution
    """
    # Define the credit cost for this operation
    REQUIRED_CREDITS = 5  # Adjust this value as needed
    
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
    
    # Check if the user has enough credits
    if not profile.has_sufficient_credits(REQUIRED_CREDITS):
        return Response(
            {
                "error": "Insufficient credits",
                "required": REQUIRED_CREDITS,
                "available": profile.credits_balance,
                "message": f"This operation requires {REQUIRED_CREDITS} credits. You have {profile.credits_balance} credits available."
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
                {"error": "Script not found"},
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
        
        # Deduct credits from the user's account
        profile.deduct_credits(REQUIRED_CREDITS)
        
        # Record the credit transaction
        CreditTransaction.objects.create(
            user=request.user,
            amount=-REQUIRED_CREDITS,
            balance_after=profile.credits_balance,
            description="Executed main.py script",
            endpoint=request.path
        )
        
        # Prepare the response
        response_data = {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "credits_used": REQUIRED_CREDITS,
            "credits_remaining": profile.credits_balance,
        }
        
        # Try to parse stdout as JSON if it looks like JSON
        if result.stdout.strip().startswith("{") and result.stdout.strip().endswith("}"):
            try:
                response_data["result"] = json.loads(result.stdout)
            except json.JSONDecodeError:
                # If it's not valid JSON, just use the raw output
                pass
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {"error": f"Failed to execute script: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
