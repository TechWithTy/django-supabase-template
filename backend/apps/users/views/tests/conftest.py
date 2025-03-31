import os
import sys
import django
import pytest
import uuid
import time
from pathlib import Path
from rest_framework.test import APIClient
from rest_framework.authentication import BaseAuthentication
from apps.users.models import UserProfile
from apps.supabase_home.auth import SupabaseAuthService
from apps.supabase_home.storage import SupabaseStorageService
from apps.supabase_home.database import SupabaseDatabaseService
from apps.supabase_home.realtime import SupabaseRealtimeService
from utils.sensitive import load_environment_files

# Load project settings
backend_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

# Load environment variables
load_environment_files()

# Test credentials
TEST_EMAIL = os.environ.get('TEST_USER_EMAIL', 'integration-test@example.com')
TEST_PASSWORD = os.environ.get('TEST_USER_PASSWORD', 'integration-test-password')
TEST_BUCKET = os.environ.get('TEST_BUCKET', 'integration-test-bucket')
TEST_TABLE = os.environ.get('TEST_TABLE', 'integration_test_table')

# Create a custom token object for testing
class SupabaseAuthToken:
    """A simple class to hold the auth token for testing"""
    def __init__(self, token):
        self.token = token

class CustomAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            # Create a mock user with an ID
            from django.contrib.auth.models import User
            user = User(username='test_user')
            # Set the token directly on the user object
            user.auth_token = token
            # Also set it as a property that matches what our views expect
            token_obj = SupabaseAuthToken(token)
            return (user, token_obj)
        return None

@pytest.fixture(scope="session")
def test_user_credentials():
    """Test user credentials for Supabase integration tests"""
    auth_service = SupabaseAuthService()
    
    # First try using existing test credentials from environment
    email = os.getenv("TEST_USER_EMAIL")
    password = os.getenv("TEST_USER_PASSWORD")
    
    if email and password:
        try:
            # Sign in with existing credentials
            signin_result = auth_service.sign_in_with_email(email=email, password=password)
            return {
                "email": email,
                "password": password,
                "id": signin_result.get("user", {}).get("id"),
                "auth_token": signin_result.get("access_token"),
                "refresh_token": signin_result.get("refresh_token")
            }
        except Exception as e:
            print(f"Warning: Could not sign in with provided TEST_USER credentials: {str(e)}")
    
    # If environment credentials aren't available or don't work, try to create a test user
    if not os.getenv("SKIP_TEST_USER_CREATION", "false").lower() == "true":
        try:
            # Generate unique test user
            unique_email = f"testuser_{uuid.uuid4()}@example.com"
            test_password = "TestPassword123!"
            
            # Create the user in Supabase
            auth_service.admin_create_user(
                email=unique_email,
                password=test_password,
                user_metadata={"name": "API Test User"},
                email_confirm=True  # Auto-confirm email
            )
            
            # Sign in to get auth token
            signin_result = auth_service.sign_in_with_email(
                email=unique_email,
                password=test_password
            )
            
            return {
                "email": unique_email,
                "password": test_password,
                "id": signin_result.get("user", {}).get("id"),
                "auth_token": signin_result.get("access_token"),
                "refresh_token": signin_result.get("refresh_token")
            }
        except Exception as e:
            print(f"Warning: Could not create test user for integration tests: {str(e)}")
    
    # If we get here, we couldn't get valid credentials
    pytest.skip("No valid test user credentials available")
    return None

@pytest.fixture(scope="function")
def refresh_test_user(test_user_credentials):
    """Refresh the test user's authentication token before each test"""
    auth_service = SupabaseAuthService()
    try:
        # Use the refresh token to get a new access token
        if test_user_credentials and test_user_credentials.get("refresh_token"):
            refresh_result = auth_service.refresh_session(test_user_credentials["refresh_token"])
            
            # Update the credentials with the new tokens
            test_user_credentials["auth_token"] = refresh_result.get("access_token")
            test_user_credentials["refresh_token"] = refresh_result.get("refresh_token")
            
            return test_user_credentials
    except Exception as e:
        print(f"Warning: Failed to refresh token: {str(e)}")
        
    # If refresh failed, try to log in again
    try:
        if test_user_credentials and test_user_credentials.get("email") and test_user_credentials.get("password"):
            signin_result = auth_service.sign_in_with_email(
                email=test_user_credentials["email"],
                password=test_user_credentials["password"]
            )
            
            # Update credentials with fresh tokens
            test_user_credentials["auth_token"] = signin_result.get("access_token")
            test_user_credentials["refresh_token"] = signin_result.get("refresh_token")
            
            return test_user_credentials
    except Exception as e:
        print(f"Warning: Failed to sign in again: {str(e)}")
    
    return test_user_credentials

@pytest.fixture(scope="function")
def authenticated_client(refresh_test_user):
    """API client authenticated with a fresh Supabase JWT token (function scoped for fresh tokens)"""
    client = APIClient()
    
    # Check if we have valid credentials
    if not refresh_test_user or not refresh_test_user.get("auth_token"):
        pytest.skip("No authentication token available")
        return None
        
    # Set the JWT token in the Authorization header
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh_test_user["auth_token"]}')    
    return client

@pytest.fixture(scope="session")
def test_django_user(test_user_credentials, users_db_setup, django_db_blocker):
    """Create a test user in the Django database
    
    This creates a Django User model instance matching the Supabase user
    for testing endpoints that require Django database user records.
    """
    with django_db_blocker.unblock():
        if not test_user_credentials or not test_user_credentials.get("id"):
            pytest.skip("No valid test user credentials available")
        
        # Import the User model
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # First create the auth user
        auth_user, auth_created = User.objects.get_or_create(
            username=test_user_credentials["email"],
            defaults={
                "email": test_user_credentials["email"],
                "first_name": "Test",
                "last_name": "User",
                "supabase_uid": test_user_credentials["id"]
            }
        )
        
        # Generate a UUID for the UserProfile
        profile_id = uuid.uuid4()
        
        # Then create or get the UserProfile
        try:
            # Try to get existing profile
            user_profile = UserProfile.objects.get(user=auth_user)
            profile_created = False
        except UserProfile.DoesNotExist:
            # Create new profile with explicit UUID
            user_profile = UserProfile.objects.create(
                id=profile_id,
                user=auth_user,
                supabase_uid=test_user_credentials["id"],
                credits_balance=1000  # Give plenty of credits for testing credit-based views
            )
            profile_created = True
        
        if not profile_created:
            # Ensure the user has enough credits for our tests
            if user_profile.credits_balance < 1000:
                user_profile.credits_balance = 1000
                user_profile.save()
        
        return user_profile

@pytest.fixture(scope="session")
def test_admin_django_user(test_django_user, django_db_blocker):
    """Create a test admin user in the Django database"""
    with django_db_blocker.unblock():
        # Make the test user an admin
        test_django_user.user.is_staff = True
        test_django_user.user.is_superuser = True
        test_django_user.user.save()
        
        return test_django_user

@pytest.fixture(scope="session")
def supabase_services():
    """Return initialized Supabase service classes"""
    return {
        "auth": SupabaseAuthService(),
        "storage": SupabaseStorageService(),
        "database": SupabaseDatabaseService(),
        "realtime": SupabaseRealtimeService()
    }

@pytest.fixture(scope="session")
def test_bucket(test_user_credentials, supabase_services, django_db_blocker):
    """Create a test bucket for storage tests"""
    # Skip if no auth token
    if not test_user_credentials or not test_user_credentials.get("auth_token"):
        pytest.skip("No authentication token available")

    # Generate a unique bucket name
    bucket_name = f"test-bucket-{uuid.uuid4().hex[:8]}"
    storage_service = supabase_services["storage"]
    auth_token = test_user_credentials["auth_token"]
    
    try:
        # Create the bucket
        storage_service.create_bucket(
            bucket_id=bucket_name,
            public=True,  # Public for easier testing
            auth_token=auth_token,
            is_admin=True
        )
        
        # Wait for Supabase to process the bucket creation
        time.sleep(3)
        
        print(f"Created test bucket: {bucket_name}")
        yield bucket_name
        
        # Clean up after tests
        try:
            storage_service.delete_bucket(
                bucket_id=bucket_name,
                auth_token=auth_token,
                is_admin=True
            )
            print(f"Deleted test bucket: {bucket_name}")
        except Exception as e:
            print(f"Warning: Failed to delete test bucket {bucket_name}: {str(e)}")
            
    except Exception as e:
        print(f"Warning: Failed to create test bucket: {str(e)}")
        pytest.skip(f"Could not create test bucket: {str(e)}")
        yield None

@pytest.fixture(scope="session")
def test_table(test_user_credentials, supabase_services, django_db_blocker):
    """Create a test table for database tests"""
    # Skip if no auth token
    if not test_user_credentials or not test_user_credentials.get("auth_token"):
        pytest.skip("No authentication token available")
    
    # Generate a unique table name
    table_name = f"test_table_{uuid.uuid4().hex[:8]}"
    database_service = supabase_services["database"]
    auth_token = test_user_credentials["auth_token"]
    
    try:
        # Create the table with proper RLS policies
        create_table_sql = f"""
        CREATE TABLE public.{table_name} (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            user_id UUID REFERENCES auth.users(id)
        );
        
        ALTER TABLE public.{table_name} ENABLE ROW LEVEL SECURITY;
        
        -- Policy for read access
        CREATE POLICY "{table_name}_select_policy" 
        ON public.{table_name} FOR SELECT USING (true);
        
        -- Policy for insert access
        CREATE POLICY "{table_name}_insert_policy" 
        ON public.{table_name} FOR INSERT 
        WITH CHECK (auth.uid() = user_id OR auth.uid() IS NOT NULL);
        
        -- Policy for update access
        CREATE POLICY "{table_name}_update_policy" 
        ON public.{table_name} FOR UPDATE 
        USING (auth.uid() = user_id) 
        WITH CHECK (auth.uid() = user_id);
        
        -- Policy for delete access
        CREATE POLICY "{table_name}_delete_policy" 
        ON public.{table_name} FOR DELETE 
        USING (auth.uid() = user_id);
        """
        
        # Execute the SQL to create the table
        database_service.execute_sql(
            query=create_table_sql,
            auth_token=auth_token
        )
        
        print(f"Created test table: {table_name}")
        yield table_name
        
        # Clean up after tests
        try:
            drop_table_sql = f"DROP TABLE IF EXISTS public.{table_name};"
            database_service.execute_sql(
                query=drop_table_sql,
                auth_token=auth_token
            )
            print(f"Dropped test table: {table_name}")
        except Exception as e:
            print(f"Warning: Failed to drop test table {table_name}: {str(e)}")
            
    except Exception as e:
        print(f"Warning: Failed to create test table: {str(e)}")
        pytest.skip(f"Could not create test table: {str(e)}")
        yield None

@pytest.fixture(scope="session")
def monkeypatch_session(request):
    """Create a session-scoped monkeypatch fixture"""
    from _pytest.monkeypatch import MonkeyPatch
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()

@pytest.fixture(scope="session")
def supabase_auth_mock(monkeypatch_session):
    """Mock the Supabase auth service to bypass real authentication"""
    def mock_verify_jwt(self, token):
        # Return a valid user payload that matches our test user
        return {
            "sub": "test-user-id",
            "email": "test@example.com",
            "exp": int(time.time()) + 3600,  # Valid for 1 hour
            "aud": "authenticated",
            "app_metadata": {},
            "user_metadata": {"name": "Test User"},
            "role": "authenticated"
        }
    
    # Use monkeypatch_session to mock the auth service verify_jwt method
    from apps.authentication.authentication import SupabaseJWTAuthentication
    monkeypatch_session.setattr(SupabaseJWTAuthentication, "verify_jwt", mock_verify_jwt)
    
    return True

@pytest.fixture(scope="session")
def users_db_setup(django_db_setup, django_db_blocker):
    """Set up the database for session-scoped fixtures"""
    pass
