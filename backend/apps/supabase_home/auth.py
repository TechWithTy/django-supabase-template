from typing import Any, Dict, List, Optional

from ._service import SupabaseService


class SupabaseAuthService(SupabaseService):
    """
    Service for interacting with Supabase Auth API.

    This class provides methods for user management, authentication,
    and session handling using Supabase Auth.
    """

    def create_user(
        self, email: str, password: str, user_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new user with email and password.

        Args:
            email: User's email address
            password: User's password
            user_metadata: Optional metadata for the user

        Returns:
            User data
        """
        data = {
            "email": email,
            "password": password,
        }

        if user_metadata:
            data["user_metadata"] = user_metadata

        return self._make_request(
            method="POST", endpoint="/auth/v1/admin/users", is_admin=True, data=data
        )

    def create_anonymous_user(self) -> Dict[str, Any]:
        """
        Create an anonymous user.

        Returns:
            Session data including user and tokens
        """
        return self._make_request(method="POST", endpoint="/auth/v1/signup", data={})

    def sign_in_with_email(
        self, email: str, password: str, is_admin: bool = False
    ) -> Dict[str, Any]:
        """
        Sign in a user with email and password.

        Args:
            email: User's email address
            password: User's password
            is_admin: Whether to use the service role key (admin access)

        Returns:
            Session data including user and tokens
        """
        return self._make_request(
            method="POST",
            endpoint="/auth/v1/token?grant_type=password",
            data={"email": email, "password": password},
            is_admin=is_admin,
        )

    def sign_in_with_id_token(self, provider: str, id_token: str) -> Dict[str, Any]:
        """
        Sign in a user with an ID token from a third-party provider.

        Args:
            provider: Provider name (e.g., 'google', 'apple')
            id_token: ID token from the provider

        Returns:
            Session data including user and tokens
        """
        return self._make_request(
            method="POST",
            endpoint="/auth/v1/token?grant_type=id_token",
            data={"provider": provider, "id_token": id_token},
        )

    def sign_in_with_otp(self, email: str) -> Dict[str, Any]:
        """
        Send a one-time password to the user's email.

        Args:
            email: User's email address

        Returns:
            Success message
        """
        return self._make_request(
            method="POST", endpoint="/auth/v1/otp", data={"email": email}
        )

    def verify_otp(self, email: str, token: str, type: str = "email") -> Dict[str, Any]:
        """
        Verify a one-time password and log in the user.

        Args:
            email: User's email address
            token: OTP token
            type: OTP type ('email', 'sms', etc.)

        Returns:
            Session data including user and tokens
        """
        return self._make_request(
            method="POST",
            endpoint="/auth/v1/verify",
            data={"email": email, "token": token, "type": type},
        )

    def sign_in_with_oauth(self, provider: str, redirect_url: str) -> Dict[str, Any]:
        """
        Get the URL to redirect the user for OAuth sign-in.

        Args:
            provider: Provider name (e.g., 'google', 'github')
            redirect_url: URL to redirect after authentication

        Returns:
            URL to redirect the user to
        """
        return self._make_request(
            method="POST",
            endpoint=f"/auth/v1/authorize?provider={provider}",
            data={"redirect_to": redirect_url},
        )

    def sign_in_with_sso(self, domain: str, redirect_url: str) -> Dict[str, Any]:
        """
        Sign in a user through SSO with a domain.

        Args:
            domain: Organization domain for SSO
            redirect_url: URL to redirect after authentication

        Returns:
            URL to redirect the user to
        """
        return self._make_request(
            method="POST",
            endpoint="/auth/v1/sso",
            data={"domain": domain, "redirect_to": redirect_url},
        )

    def sign_out(self, auth_token: str) -> Dict[str, Any]:
        """
        Sign out a user.

        Args:
            auth_token: User's JWT token

        Returns:
            Success message
        """
        return self._make_request(
            method="POST", endpoint="/auth/v1/logout", auth_token=auth_token
        )

    def reset_password(
        self, email: str, redirect_url: Optional[str] = None, is_admin: bool = False
    ) -> Dict[str, Any]:
        """
        Send a password reset email to the user.

        Args:
            email: User's email address
            redirect_url: URL to redirect after password reset
            is_admin: Whether to use the service role key (admin access)

        Returns:
            Success message
        """
        data = {"email": email}
        if redirect_url:
            data["redirect_to"] = redirect_url

        return self._make_request(method="POST", endpoint="/auth/v1/recover", data=data, is_admin=is_admin)

    def get_session(self, auth_token: str) -> Dict[str, Any]:
        """
        Retrieve the user's session.

        Args:
            auth_token: User's JWT token

        Returns:
            Session data
        """
        return self._make_request(
            method="GET", endpoint="/auth/v1/user", auth_token=auth_token
        )

    def refresh_session(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh the user's session with a refresh token.

        Args:
            refresh_token: User's refresh token

        Returns:
            New session data
        """
        return self._make_request(
            method="POST",
            endpoint="/auth/v1/token?grant_type=refresh_token",
            data={"refresh_token": refresh_token},
        )

    def get_user(self, user_id: str) -> Dict[str, Any]:
        """
        Retrieve a user by ID (admin only).

        Args:
            user_id: User's ID

        Returns:
            User data
        """
        return self._make_request(
            method="GET", endpoint=f"/auth/v1/admin/users/{user_id}", is_admin=True
        )

    def update_user(self, user_id: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a user's data (admin only).

        Args:
            user_id: User's ID
            user_data: Data to update

        Returns:
            Updated user data
        """
        return self._make_request(
            method="PUT",
            endpoint=f"/auth/v1/admin/users/{user_id}",
            is_admin=True,
            data=user_data,
        )

    def get_user_identities(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve identities linked to a user (admin only).

        Args:
            user_id: User's ID

        Returns:
            List of identities
        """
        user = self.get_user(user_id)
        return user.get("identities", [])

    def link_identity(
        self, auth_token: str, provider: str, redirect_url: str
    ) -> Dict[str, Any]:
        """
        Link an identity to a user.

        Args:
            auth_token: User's JWT token
            provider: Provider name (e.g., 'google', 'github')
            redirect_url: URL to redirect after linking

        Returns:
            URL to redirect the user to
        """
        return self._make_request(
            method="POST",
            endpoint=f"/auth/v1/user/identities/authorize?provider={provider}",
            auth_token=auth_token,
            data={"redirect_to": redirect_url},
        )

    def unlink_identity(self, auth_token: str, identity_id: str) -> Dict[str, Any]:
        """
        Unlink an identity from a user.

        Args:
            auth_token: User's JWT token
            identity_id: Identity ID to unlink

        Returns:
            Success message
        """
        return self._make_request(
            method="DELETE",
            endpoint=f"/auth/v1/user/identities/{identity_id}",
            auth_token=auth_token,
        )

    def set_session_data(self, auth_token: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set the session data.

        Args:
            auth_token: User's JWT token
            data: Session data to set

        Returns:
            Updated session data
        """
        return self._make_request(
            method="PUT",
            endpoint="/auth/v1/user",
            auth_token=auth_token,
            data={"data": data},
        )

    def get_user_by_token(self, token: str) -> Dict[str, Any]:
        """
        Get user information from a JWT token.

        Args:
            token: JWT token

        Returns:
            User data
        """
        # Call the user endpoint with the token
        return self._make_request(
            method="GET",
            endpoint="/auth/v1/user",
            auth_token=token,
        )

    # MFA methods
    def enroll_mfa_factor(
        self, auth_token: str, factor_type: str = "totp"
    ) -> Dict[str, Any]:
        """
        Enroll a multi-factor authentication factor.

        Args:
            auth_token: User's JWT token
            factor_type: Factor type (default: 'totp')

        Returns:
            Factor data including QR code
        """
        return self._make_request(
            method="POST",
            endpoint="/auth/v1/factors",
            auth_token=auth_token,
            data={"factor_type": factor_type},
        )

    def create_mfa_challenge(self, auth_token: str, factor_id: str) -> Dict[str, Any]:
        """
        Create a multi-factor authentication challenge.

        Args:
            auth_token: User's JWT token
            factor_id: Factor ID

        Returns:
            Challenge data
        """
        return self._make_request(
            method="POST",
            endpoint="/auth/v1/factors/challenges",
            auth_token=auth_token,
            data={"factor_id": factor_id},
        )

    def verify_mfa_challenge(
        self, auth_token: str, factor_id: str, challenge_id: str, code: str
    ) -> Dict[str, Any]:
        """
        Verify a multi-factor authentication challenge.

        Args:
            auth_token: User's JWT token
            factor_id: Factor ID
            challenge_id: Challenge ID
            code: Verification code

        Returns:
            Verification result
        """
        return self._make_request(
            method="POST",
            endpoint="/auth/v1/factors/verify",
            auth_token=auth_token,
            data={"factor_id": factor_id, "challenge_id": challenge_id, "code": code},
        )

    def unenroll_mfa_factor(self, auth_token: str, factor_id: str) -> Dict[str, Any]:
        """
        Unenroll a multi-factor authentication factor.

        Args:
            auth_token: User's JWT token
            factor_id: Factor ID

        Returns:
            Success message
        """
        return self._make_request(
            method="DELETE",
            endpoint=f"/auth/v1/factors/{factor_id}",
            auth_token=auth_token,
        )

    def list_users(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """
        List all users (admin only).

        Args:
            page: Page number for pagination
            per_page: Number of users per page

        Returns:
            List of users
        """
        return self._make_request(
            method="GET",
            endpoint=f"/auth/v1/admin/users?page={page}&per_page={per_page}",
            is_admin=True,
        )

    def admin_create_user(
        self,
        email: str,
        password: str,
        user_metadata: Optional[Dict[str, Any]] = None,
        email_confirm: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a new user with admin privileges (bypassing email verification if needed).

        Args:
            email: User's email address
            password: User's password
            user_metadata: Optional metadata for the user
            email_confirm: Whether to auto-confirm the user's email

        Returns:
            User data
        """
        data = {
            "email": email,
            "password": password,
            "email_confirm": email_confirm,
        }

        if user_metadata:
            data["user_metadata"] = user_metadata

        return self._make_request(
            method="POST", endpoint="/auth/v1/admin/users", is_admin=True, data=data
        )
