from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

# Import the SupabaseAuthService directly
from apps.supabase_home.auth import (
    SupabaseAuthService,
    # Import specific functions from SupabaseAuthService
)

from ..models import UserProfile
from ..serializers import UserSerializer, UserProfileSerializer

auth_service = SupabaseAuthService()


@api_view(["POST"])
def signup(request: Request) -> Response:
    """
    Create a new user with email and password.
    """
    email = request.data.get("email")
    password = request.data.get("password")
    first_name = request.data.get("first_name", "")
    last_name = request.data.get("last_name", "")
    
    if not email or not password:
        return Response(
            {"error": "Email and password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    try:
        # Create user metadata with first and last name if provided
        user_metadata = {}
        if first_name:
            user_metadata["first_name"] = first_name
        if last_name:
            user_metadata["last_name"] = last_name
            
        # Create the user in Supabase
        user = auth_service.create_user(
            email=email,
            password=password,
            user_metadata=user_metadata
        )
        
        # Try to sign in the user to get a session, but don't fail if email confirmation is required
        session = None
        try:
            session = auth_service.sign_in_with_email(
                email=email,
                password=password
            )
        except Exception as signin_error:
            # Check if the error is due to email not being confirmed
            error_message = str(signin_error)
            if "email_not_confirmed" in error_message:
                # Log a warning but continue with the signup process
                print(f"Warning: Email not confirmed for {email}. User created but not signed in.")
            else:
                # For other sign-in errors, we still want to log them but not fail the signup
                print(f"Warning: Failed to sign in after signup: {error_message}")
        
        # Always include both user and session in the response
        # If session is None, it will be serialized as null in the JSON response
        response_data = {
            "user": user,
            "session": session
        }
        
        # Add a message if email confirmation is required
        if session is None:
            response_data["message"] = "User created successfully. Please confirm your email before signing in."
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response(
            {"error": f"Failed to create user: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def create_anonymous_user(request: Request) -> Response:
    """
    Create an anonymous user in Supabase.
    """
    try:
        response = auth_service.create_anonymous_user()
        return Response(response, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response(
            {"error": f"Failed to create anonymous user: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def sign_in_with_email(request: Request) -> Response:
    """
    Sign in a user with email and password.
    """
    email = request.data.get("email")
    password = request.data.get("password")

    if not email or not password:
        return Response(
            {"error": "Email and password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        response = auth_service.sign_in_with_email(email=email, password=password)
        
        # Extract user data from the response
        user = {
            'id': response.get('user', {}).get('id') if 'user' in response else None,
            'email': email,
            # Add other user fields as needed
        }
        
        # Format the response to match the expected structure
        return Response(
            {
                "user": user,
                "session": response,  # Use the entire response as the session data
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to sign in: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def sign_in_with_id_token(request: Request) -> Response:
    """
    Sign in with an ID token from a third-party provider.
    """
    provider = request.data.get("provider")
    id_token = request.data.get("id_token")

    if not provider or not id_token:
        return Response(
            {"error": "Provider and ID token are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        response = auth_service.sign_in_with_id_token(
            provider=provider, id_token=id_token
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to sign in with ID token: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def sign_in_with_otp(request: Request) -> Response:
    """
    Sign in with a one-time password (OTP) sent to email.
    """
    email = request.data.get("email")

    if not email:
        return Response(
            {"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        response = auth_service.sign_in_with_otp(email=email)
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to send OTP: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def verify_otp(request: Request) -> Response:
    """
    Verify a one-time password (OTP).
    """
    email = request.data.get("email")
    token = request.data.get("token")
    type = request.data.get("type", "email")

    if not email or not token:
        return Response(
            {"error": "Email and token are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        response = auth_service.verify_otp(email=email, token=token, type=type)
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to verify OTP: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def sign_in_with_oauth(request: Request) -> Response:
    """
    Get the URL to redirect the user for OAuth sign-in.
    """
    provider = request.data.get("provider")
    redirect_url = request.data.get("redirect_url")

    if not provider or not redirect_url:
        return Response(
            {"error": "Provider and redirect URL are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        response = auth_service.sign_in_with_oauth(
            provider=provider, redirect_url=redirect_url
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to sign in with OAuth: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def sign_in_with_sso(request: Request) -> Response:
    """
    Sign in with Single Sign-On (SSO).
    """
    domain = request.data.get("domain")
    redirect_url = request.data.get("redirect_url")

    if not domain or not redirect_url:
        return Response(
            {"error": "Domain and redirect URL are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        response = auth_service.sign_in_with_sso(
            domain=domain, redirect_url=redirect_url
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to sign in with SSO: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def sign_out(request: Request) -> Response:
    """
    Sign out a user.
    """
    # Try to get auth token from request data first
    auth_token = request.data.get("auth_token")
    
    # If not in request data, try to get from Authorization header
    if not auth_token:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            auth_token = auth_header.split(' ')[1]
    
    if not auth_token:
        return Response(
            {"error": "Auth token is required"}, status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        auth_service.sign_out(auth_token=auth_token)
        # Return 204 No Content on successful logout as per REST conventions
        return Response(status=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        error_message = str(e)
        # Check if the error is related to authentication
        if "401" in error_message or "403" in error_message or "session_not_found" in error_message:
            # If the session is already invalid, we can consider this a successful logout
            # This handles the case where the token is expired or already invalidated
            print(f"Warning: Session already invalid during logout: {error_message}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(
                {"error": f"Failed to sign out: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@api_view(["POST"])
def reset_password(request: Request) -> Response:
    """
    Send a password reset email to the user.
    """
    email = request.data.get("email")
    redirect_url = request.data.get("redirect_url")

    if not email:
        return Response(
            {"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        response = auth_service.reset_password(email=email, redirect_url=redirect_url)
        return Response({"message": "Password reset email sent"}, status=status.HTTP_200_OK)
    except Exception as e:
        error_message = str(e)
        # Check if the error is due to rate limiting
        if "over_email_send_rate_limit" in error_message or "429" in error_message:
            # For security reasons, don't reveal that we hit a rate limit
            # This prevents user enumeration attacks
            print(f"Warning: Rate limit exceeded for password reset: {error_message}")
            return Response(
                {"message": "If your email exists in our system, you will receive a password reset link"},
                status=status.HTTP_200_OK
            )
        else:
            # Log the error but still return a generic success message for security
            print(f"Error in password reset: {error_message}")
            return Response(
                {"message": "If your email exists in our system, you will receive a password reset link"},
                status=status.HTTP_200_OK
            )


@api_view(["GET"])
def get_session(request: Request) -> Response:
    """
    Retrieve the user's session.
    """
    auth_token = request.headers.get("Authorization")

    if not auth_token:
        return Response(
            {"error": "Auth token is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Remove 'Bearer ' prefix if present
    if auth_token.startswith("Bearer "):
        auth_token = auth_token[7:]

    try:
        response = auth_service.get_session(auth_token=auth_token)
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to get session: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def refresh_session(request: Request) -> Response:
    """
    Refresh a user's session using a refresh token.
    """
    refresh_token = request.data.get("refresh_token")

    if not refresh_token:
        return Response(
            {"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        response = auth_service.refresh_session(refresh_token=refresh_token)
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to refresh session: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def get_user(request: Request, user_id: str) -> Response:
    """
    Retrieve a user by ID (admin only).
    """
    try:
        response = auth_service.get_user(user_id=user_id)
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to get user: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["PUT"])
@permission_classes([permissions.IsAdminUser])
def update_user(request: Request, user_id: str) -> Response:
    """
    Update a user's data (admin only).
    """
    user_data = request.data

    try:
        response = auth_service.update_user(user_id=user_id, user_data=user_data)
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to update user: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def get_user_identities(request: Request, user_id: str) -> Response:
    """
    Retrieve identities linked to a user (admin only).
    """
    try:
        response = auth_service.get_user_identities(user_id=user_id)
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to get user identities: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def link_identity(request: Request) -> Response:
    """
    Link an identity to a user.
    """
    auth_token = request.data.get("auth_token")
    provider = request.data.get("provider")
    redirect_url = request.data.get("redirect_url")

    if not auth_token or not provider or not redirect_url:
        return Response(
            {"error": "Auth token, provider, and redirect URL are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        response = auth_service.link_identity(
            auth_token=auth_token, provider=provider, redirect_url=redirect_url
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to link identity: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def unlink_identity(request: Request) -> Response:
    """
    Unlink an identity from a user.
    """
    auth_token = request.data.get("auth_token")
    identity_id = request.data.get("identity_id")

    if not auth_token or not identity_id:
        return Response(
            {"error": "Auth token and identity ID are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        response = auth_service.unlink_identity(
            auth_token=auth_token, identity_id=identity_id
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to unlink identity: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def set_session_data(request: Request) -> Response:
    """
    Set the session data.
    """
    auth_token = request.data.get("auth_token")
    data = request.data.get("data", {})

    if not auth_token:
        return Response(
            {"error": "Auth token is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        response = auth_service.set_session_data(auth_token=auth_token, data=data)
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to set session data: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def enroll_mfa_factor(request: Request) -> Response:
    """
    Enroll a multi-factor authentication factor.
    """
    auth_token = request.data.get("auth_token")
    factor_type = request.data.get("factor_type", "totp")

    if not auth_token:
        return Response(
            {"error": "Auth token is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        response = auth_service.enroll_mfa_factor(
            auth_token=auth_token, factor_type=factor_type
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to enroll MFA factor: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def create_mfa_challenge(request: Request) -> Response:
    """
    Create a multi-factor authentication challenge.
    """
    auth_token = request.data.get("auth_token")
    factor_id = request.data.get("factor_id")

    if not auth_token or not factor_id:
        return Response(
            {"error": "Auth token and factor ID are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        response = auth_service.create_mfa_challenge(
            auth_token=auth_token, factor_id=factor_id
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to create MFA challenge: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def verify_mfa_challenge(request: Request) -> Response:
    """
    Verify a multi-factor authentication challenge.
    """
    auth_token = request.data.get("auth_token")
    factor_id = request.data.get("factor_id")
    challenge_id = request.data.get("challenge_id")
    code = request.data.get("code")

    if not auth_token or not factor_id or not challenge_id or not code:
        return Response(
            {"error": "Auth token, factor ID, challenge ID, and code are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        response = auth_service.verify_mfa_challenge(
            auth_token=auth_token,
            factor_id=factor_id,
            challenge_id=challenge_id,
            code=code,
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to verify MFA challenge: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def unenroll_mfa_factor(request: Request) -> Response:
    """
    Unenroll a multi-factor authentication factor.
    """
    auth_token = request.data.get("auth_token")
    factor_id = request.data.get("factor_id")

    if not auth_token or not factor_id:
        return Response(
            {"error": "Auth token and factor ID are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        response = auth_service.unenroll_mfa_factor(
            auth_token=auth_token, factor_id=factor_id
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to unenroll MFA factor: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def list_users(request: Request) -> Response:
    """
    List all users (admin only).
    """
    page = request.query_params.get("page", 1)
    per_page = request.query_params.get("per_page", 50)

    try:
        response = auth_service.list_users(page=int(page), per_page=int(per_page))
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to list users: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_current_user(request: Request) -> Response:
    """
    Retrieve the current authenticated user's information.
    """
    try:
        # Get the JWT token from the request
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return Response(
                {"error": "Invalid authorization header"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        
        token = auth_header.split(' ')[1]
        
        # Get user information from the token
        user_info = auth_service.get_user_by_token(token)
        
        return Response(user_info, status=status.HTTP_200_OK)
    except Exception as e:
        error_message = str(e)
        # Check if the error is related to authentication
        if "401" in error_message or "403" in error_message or "session_not_found" in error_message or "authentication" in error_message.lower():
            # Return 401 Unauthorized for authentication-related errors
            return Response(
                {"error": "Authentication failed"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        else:
            # For other errors, return 500 Internal Server Error
            return Response(
                {"error": f"Failed to get user information: {error_message}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
