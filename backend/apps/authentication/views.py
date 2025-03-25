from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
import logging
from .models import UserData

# Import the SupabaseAuthService directly
from apps.supabase.auth import SupabaseAuthService

User = get_user_model()
logger = logging.getLogger("apps.authentication")

# Initialize the Supabase Auth Service
auth_service = SupabaseAuthService()


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request: Request) -> Response:
    """
    Health check endpoint to verify the API is running.
    """
    return Response({"status": "ok"}, status=status.HTTP_200_OK)


# User Registration Endpoint
@api_view(["POST"])
@permission_classes([AllowAny])
def register(request: Request) -> Response:
    """
    Endpoint for user registration using Supabase Auth.

    This endpoint creates a new user in Supabase and in the local database.
    """
    email = request.data.get("email")
    password = request.data.get("password")
    user_metadata = request.data.get("user_metadata", {})

    if not email or not password:
        return Response(
            {"error": "Email and password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Use the Supabase auth service to create a user
        supabase_response = auth_service.create_user(
            email=email, password=password, user_metadata=user_metadata
        )

        # If successful, create a local user record
        if "id" in supabase_response:
            supabase_uid = supabase_response["id"]

            # Create or update the Django user
            user, created = User.objects.update_or_create(
                email=email, defaults={"username": email, "supabase_uid": supabase_uid}
            )

            if created:
                user.set_password(password)
                user.save()
                # Create empty user data record
                UserData.objects.create(user=user)

            return Response(
                {
                    "message": "User registered successfully",
                    "user": {"id": supabase_uid, "email": email},
                },
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )
        else:
            return Response(
                {"error": "Registration failed", "details": supabase_response},
                status=status.HTTP_400_BAD_REQUEST,
            )

    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return Response(
            {"error": "Registration failed", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# User Login Endpoint
@api_view(["POST"])
@permission_classes([AllowAny])
def login(request: Request) -> Response:
    """
    Endpoint for user login using Supabase Auth.

    This endpoint authenticates a user and returns a JWT token.
    """
    email = request.data.get("email")
    password = request.data.get("password")

    if not email or not password:
        return Response(
            {"error": "Email and password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Use the Supabase auth service to sign in
        supabase_response = auth_service.sign_in_with_email(
            email=email, password=password
        )

        # Return the tokens
        if "access_token" in supabase_response:
            return Response(
                {
                    "access_token": supabase_response["access_token"],
                    "refresh_token": supabase_response.get("refresh_token"),
                    "user": supabase_response.get("user", {}),
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"error": "Authentication failed", "details": supabase_response},
                status=status.HTTP_401_UNAUTHORIZED,
            )

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return Response(
            {"error": "Authentication failed", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# OAuth Login Endpoint
@api_view(["POST"])
@permission_classes([AllowAny])
def oauth_login(request: Request) -> Response:
    """
    Endpoint for OAuth login using Supabase Auth.

    This endpoint processes OAuth tokens and returns user session data.
    """
    provider = request.data.get("provider")
    redirect_url = request.data.get("redirect_url")

    if not provider or not redirect_url:
        return Response(
            {"error": "Provider and redirect_url are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Use the Supabase auth service to get OAuth URL
        supabase_response = auth_service.sign_in_with_oauth(
            provider=provider, redirect_url=redirect_url
        )

        # Return the OAuth URL
        if "url" in supabase_response:
            return Response(
                {"url": supabase_response["url"]}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"error": "OAuth initialization failed", "details": supabase_response},
                status=status.HTTP_400_BAD_REQUEST,
            )

    except Exception as e:
        logger.error(f"OAuth login error: {str(e)}")
        return Response(
            {"error": "OAuth authentication failed", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Password Reset Endpoint
@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request: Request) -> Response:
    """
    Endpoint for password reset using Supabase Auth.

    This endpoint sends a password reset link to the user's email.
    """
    email = request.data.get("email")
    redirect_url = request.data.get("redirect_url")

    if not email:
        return Response(
            {"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Use the Supabase auth service to send reset password email
        auth_service.reset_password(email=email, redirect_url=redirect_url)

        # Return success message
        return Response(
            {"message": "Password reset email sent"}, status=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        return Response(
            {"error": "Password reset failed", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Get Current User Endpoint
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_info(request: Request) -> Response:
    """
    Get information about the authenticated user.
    """
    user = request.user

    try:
        # Get the JWT token from the request
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else None

        if token:
            # Get user data from Supabase using the token
            supabase_user = auth_service.get_session(token)

            # Try to get user data
            try:
                user_data = UserData.objects.get(user=user)
                profile_data = user_data.profile_data
                preferences = user_data.preferences
            except UserData.DoesNotExist:
                profile_data = {}
                preferences = {}

            # Combine Django user data with Supabase user data
            user_data = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "supabase_id": user.supabase_uid,
                "oauth_provider": user.oauth_provider,
                "profile_data": profile_data,
                "preferences": preferences,
                "supabase_data": supabase_user,
            }

            return Response(user_data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "No authentication token provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    except Exception as e:
        logger.error(f"User info error: {str(e)}")
        return Response(
            {"error": "Failed to retrieve user information", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request: Request) -> Response:
    """
    Endpoint for user logout using Supabase Auth.

    This endpoint signs out the user from Supabase.
    """
    try:
        # Get the JWT token from the request
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

            # Use the Supabase auth service to sign out
            auth_service.sign_out(auth_token=token)

            # Return success response
            return Response(
                {"message": "Logged out successfully"}, status=status.HTTP_200_OK
            )

        return Response(
            {"error": "No authentication token provided"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return Response(
            {"error": "Logout failed", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# User Data CRUD Endpoints
class UserDataView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        """
        Create user data for the authenticated user.
        """
        user = request.user

        try:
            # Check if user data already exists
            user_data, created = UserData.objects.get_or_create(user=user)

            # Update profile data and preferences
            if "profile_data" in request.data:
                user_data.profile_data = request.data["profile_data"]

            if "preferences" in request.data:
                user_data.preferences = request.data["preferences"]

            user_data.save()

            return Response(
                {
                    "message": "User data created successfully",
                    "profile_data": user_data.profile_data,
                    "preferences": user_data.preferences,
                },
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Create user data error: {str(e)}")
            return Response(
                {"error": "Failed to create user data", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def get(self, request: Request) -> Response:
        """
        Get user data for the authenticated user.
        """
        user = request.user

        try:
            # Get user data
            try:
                user_data = UserData.objects.get(user=user)
                return Response(
                    {
                        "profile_data": user_data.profile_data,
                        "preferences": user_data.preferences,
                    },
                    status=status.HTTP_200_OK,
                )
            except UserData.DoesNotExist:
                return Response(
                    {"error": "User data not found"}, status=status.HTTP_404_NOT_FOUND
                )

        except Exception as e:
            logger.error(f"Get user data error: {str(e)}")
            return Response(
                {"error": "Failed to retrieve user data", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def put(self, request: Request) -> Response:
        """
        Update user data for the authenticated user.
        """
        user = request.user

        try:
            # Get user data
            try:
                user_data = UserData.objects.get(user=user)

                # Update profile data and preferences
                if "profile_data" in request.data:
                    user_data.profile_data = request.data["profile_data"]

                if "preferences" in request.data:
                    user_data.preferences = request.data["preferences"]

                user_data.save()

                return Response(
                    {
                        "message": "User data updated successfully",
                        "profile_data": user_data.profile_data,
                        "preferences": user_data.preferences,
                    },
                    status=status.HTTP_200_OK,
                )

            except UserData.DoesNotExist:
                return Response(
                    {"error": "User data not found"}, status=status.HTTP_404_NOT_FOUND
                )

        except Exception as e:
            logger.error(f"Update user data error: {str(e)}")
            return Response(
                {"error": "Failed to update user data", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request: Request) -> Response:
        """
        Delete user data for the authenticated user.
        """
        user = request.user

        try:
            # Get user data
            try:
                user_data = UserData.objects.get(user=user)
                user_data.profile_data = {}
                user_data.preferences = {}
                user_data.save()

                return Response(
                    {"message": "User data reset successfully"},
                    status=status.HTTP_200_OK,
                )

            except UserData.DoesNotExist:
                return Response(
                    {"error": "User data not found"}, status=status.HTTP_404_NOT_FOUND
                )

        except Exception as e:
            logger.error(f"Delete user data error: {str(e)}")
            return Response(
                {"error": "Failed to delete user data", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
