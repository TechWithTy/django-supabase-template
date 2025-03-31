from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.request import Request
from rest_framework.response import Response
from django.core.cache import cache
import hashlib
import logging
import re

# Import the SupabaseAuthService directly
from apps.supabase_home.auth import SupabaseAuthService

# Import custom throttling classes
from apps.authentication.throttling import IPRateThrottle, IPBasedUserRateThrottle

logger = logging.getLogger(__name__)

auth_service = SupabaseAuthService()


def validate_password_strength(password):
    """
    Validate that the password meets the minimum security requirements.
    
    Requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit
    - Contains at least one special character
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, ""


def validate_email_format(email):
    """
    Validate that the email is in a correct format.
    
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        validate_email(email)
        return True, ""
    except ValidationError:
        return False, "Invalid email format"


@api_view(["POST"])
@throttle_classes([IPRateThrottle])
def signup(request: Request) -> Response:
    """
    Create a new user with email and password.
    """
    email = request.data.get("email")
    password = request.data.get("password")

    # Validate required fields
    if not email or not password:
        return Response(
            {"error": "Email and password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate email format
    try:
        validate_email(email)
    except ValidationError:
        return Response(
            {"error": "Invalid email format"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate password strength
    if len(password) < 8:
        return Response(
            {"error": "Password must be at least 8 characters long"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check for complexity (uppercase, lowercase, numbers, special chars)
    if not (re.search(r'[A-Z]', password) and 
            re.search(r'[a-z]', password) and 
            re.search(r'[0-9]', password) and 
            re.search(r'[!@#$%^&*(),.?":{}|<>]', password)):
        return Response(
            {"error": "Password must contain uppercase, lowercase, numbers, and special characters"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Call auth service to create user
        auth_result = auth_service.sign_up(email=email, password=password)
        
        # Return success response
        sanitized_response = {
            "message": "User created successfully",
            "user_id": auth_result.get("user", {}).get("id", "")
        }
        return Response(sanitized_response, status=status.HTTP_201_CREATED)
    except Exception as e:
        logger.error("Signup error: %s", str(e))
        # Don't expose detailed error information to client
        if "already exists" in str(e).lower() or "email already registered" in str(e).lower():
            return Response(
                {"error": "User with this email already exists"},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            {"error": "Failed to create user"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@throttle_classes([IPRateThrottle])
def create_anonymous_user(request: Request) -> Response:
    """
    Create an anonymous user in Supabase.
    """
    try:
        auth_service.create_anonymous_user()
        logger.info("Anonymous user created successfully")
        return Response(status=status.HTTP_201_CREATED)
    except Exception as e:
        error_message = str(e)
        logger.error(f"Anonymous user creation failed: {error_message}")
        return Response(
            {"error": "Failed to create anonymous user"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@throttle_classes([IPRateThrottle])
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
    
    # Validate email format
    is_valid_email, email_error = validate_email_format(email)
    if not is_valid_email:
        return Response(
            {"error": email_error},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        response = auth_service.sign_in_with_email(email=email, password=password)
        
        # Extract user data from the response
        user = None
        if 'user' in response and response['user']:
            user = {
                'id': response['user'].get('id'),
                'email': email,
                # Add other non-sensitive user fields as needed
            }
        
        # Format the response to match the expected structure
        result = {
            "session": response,  # Use the entire response as the session data
        }
        
        if user:
            result["user"] = user
            
        # Log successful sign-in (without the password)
        logger.info(f"User signed in: {email}")
            
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        error_message = str(e)
        logger.warning(f"Sign-in failed for user {email}: {error_message}")
        
        # Return appropriate error messages based on the exception
        if "invalid login credentials" in error_message or "invalid email or password" in error_message:
            return Response(
                {"error": "Invalid email or password"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        elif "email not confirmed" in error_message:
            return Response(
                {"error": "Email not confirmed. Please check your inbox and confirm your email"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        else:
            return Response(
                {"error": "Authentication failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@api_view(["POST"])
@throttle_classes([IPRateThrottle])
def sign_in_with_id_token(request: Request) -> Response:
    """
    Sign in with an ID token from a third-party provider.
    """
    provider = request.data.get("provider", "").strip().lower()
    id_token = request.data.get("id_token", "").strip()

    if not provider or not id_token:
        return Response(
            {"error": "Provider and ID token are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
        
    # Validate provider
    valid_providers = ["google", "facebook", "twitter", "github", "apple"]
    if provider not in valid_providers:
        return Response(
            {"error": f"Invalid provider. Must be one of: {', '.join(valid_providers)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        response = auth_service.sign_in_with_id_token(
            provider=provider, id_token=id_token
        )
        
        # Log successful OAuth sign-in
        logger.info(f"User signed in via {provider} OAuth")
        
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        error_message = str(e)
        logger.error(f"OAuth sign-in failed with {provider}: {error_message}")
        
        return Response(
            {"error": "Failed to authenticate with provided token"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@throttle_classes([IPRateThrottle])
def sign_in_with_otp(request: Request) -> Response:
    """
    Sign in with a one-time password (OTP) sent to email.
    """
    email = request.data.get("email")

    if not email:
        return Response(
            {"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST
        )
        
    # Validate email format
    is_valid_email, email_error = validate_email_format(email)
    if not is_valid_email:
        return Response(
            {"error": email_error},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        auth_service.sign_in_with_otp(email=email)
        
        # Log OTP email sent
        logger.info(f"OTP email sent to: {email}")
        
        return Response(
            {"message": "If your email exists in our system, a one-time login link has been sent"},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        error_message = str(e)
        logger.error(f"Failed to send OTP to {email}: {error_message}")
        
        # Don't expose whether the email exists or not (for privacy)
        return Response(
            {"message": "If your email exists in our system, a one-time login link has been sent"},
            status=status.HTTP_200_OK
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
        auth_result = auth_service.verify_otp(email=email, token=token, type=type)
        return Response(auth_result, status=status.HTTP_200_OK)
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
    Request a password reset email.
    """
    email = request.data.get("email")

    # Validate required fields
    if not email:
        return Response(
            {"error": "Email is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate email format
    try:
        validate_email(email)
    except ValidationError:
        return Response(
            {"error": "Invalid email format"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Call auth service to send password reset email
        auth_service.reset_password_for_email(email)
        
        # For security reasons, always return success even if email doesn't exist
        return Response(
            {"message": "Password reset instructions sent to email if it exists"},
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        logger.error("Error sending password reset: %s", str(e))
        # For security reasons, don't reveal if the email exists or not
        return Response(
            {"message": "Password reset instructions sent to email if it exists"},
            status=status.HTTP_200_OK,
        )


@api_view(["POST"])
def reset_password_with_token(request: Request) -> Response:
    """
    Reset a user's password using a token.
    """
    token = request.data.get("token")
    new_password = request.data.get("new_password")

    # Validate required fields
    if not token or not new_password:
        return Response(
            {"error": "Token and new_password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate password strength
    if len(new_password) < 8:
        return Response(
            {"error": "Password must be at least 8 characters long"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check for complexity (uppercase, lowercase, numbers, special chars)
    if not (re.search(r'[A-Z]', new_password) and 
            re.search(r'[a-z]', new_password) and 
            re.search(r'[0-9]', new_password) and 
            re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password)):
        return Response(
            {"error": "Password must contain uppercase, lowercase, numbers, and special characters"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Call auth service to reset password with token
        auth_service.reset_password_with_token(token, new_password)
        
        return Response(
            {"message": "Password has been reset successfully"},
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        logger.error("Error resetting password: %s", str(e))
        return Response(
            {"error": "Failed to reset password"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
@throttle_classes([IPRateThrottle, IPBasedUserRateThrottle])
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
        
        # Generate a cache key based on the token
        # Use a hash for security (avoid storing tokens in cache keys)
        token_hash = hashlib.md5(token.encode()).hexdigest()
        cache_key = f"user_info:{token_hash}"
        
        # Try to get user info from cache first
        user_info = cache.get(cache_key)
        
        if user_info is None:
            # Cache miss - get user information from the token
            logger.debug("Cache miss for user info, fetching from auth service")
            user_info = auth_service.get_user_by_token(token)
            
            # Cache the result for 5 minutes (300 seconds)
            # Short timeout to ensure we don't serve stale user data for too long
            cache.set(cache_key, user_info, timeout=300)
        else:
            logger.debug("Cache hit for user info")
        
        return Response(user_info, status=status.HTTP_200_OK)
    except Exception as e:
        error_message = str(e)
        
        # Log the error for debugging
        logger.error(f"Error retrieving current user: {error_message}")
        
        if "token is invalid" in error_message.lower() or "token has expired" in error_message.lower():
            return Response(
                {"error": "Authentication token is invalid or has expired"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        
        return Response(
            {"error": f"Failed to retrieve user information: {error_message}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def request_change_email(request: Request) -> Response:
    """
    Request to change the email address of a user.
    """
    email = request.data.get("email")

    # Validate required fields
    if not email:
        return Response(
            {"error": "Email is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate email format
    try:
        validate_email(email)
    except ValidationError:
        return Response(
            {"error": "Invalid email format"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Call auth service to request an email change
        auth_service.request_change_email(email)
        
        return Response(
            {"message": "Email change request sent successfully"},
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        logger.error("Error requesting email change: %s", str(e))
        return Response(
            {"error": "Failed to request email change"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def sign_in_with_password(request: Request) -> Response:
    """
    Sign in with email and password.
    """
    email = request.data.get("email")
    password = request.data.get("password")

    # Validate required fields
    if not email or not password:
        return Response(
            {"error": "Email and password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate email format
    try:
        validate_email(email)
    except ValidationError:
        return Response(
            {"error": "Invalid email format"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Call auth service
        auth_result = auth_service.sign_in_with_password(email=email, password=password)
        
        # Return success response with auth data
        # Be careful not to expose sensitive information here
        return Response(auth_result, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error("Login error: %s", str(e))
        # Don't reveal specific error details to the client for security
        return Response(
            {"error": "Authentication failed"},
            status=status.HTTP_401_UNAUTHORIZED,
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def change_password(request: Request) -> Response:
    """
    Change the password for an authenticated user.
    """
    current_password = request.data.get("current_password")
    new_password = request.data.get("new_password")

    # Validate required fields
    if not current_password or not new_password:
        return Response(
            {"error": "Current password and new password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate password strength
    if len(new_password) < 8:
        return Response(
            {"error": "Password must be at least 8 characters long"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check for complexity (uppercase, lowercase, numbers, special chars)
    if not (re.search(r'[A-Z]', new_password) and 
            re.search(r'[a-z]', new_password) and 
            re.search(r'[0-9]', new_password) and 
            re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password)):
        return Response(
            {"error": "Password must contain uppercase, lowercase, numbers, and special characters"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get the authentication token from the request
        auth_token = request.auth.token if hasattr(request, "auth") and hasattr(request.auth, "token") else None
        
        if not auth_token:
            return Response(
                {"error": "Authentication token is required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        
        # Call auth service to change the password
        auth_service.change_password(auth_token, current_password, new_password)
        
        return Response(
            {"message": "Password changed successfully"},
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        logger.error("Error changing password: %s", str(e))
        return Response(
            {"error": "Failed to change password"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
