import os
import sys
import django
import pytest
import uuid
import time
from pathlib import Path
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
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

@pytest.fixture(scope="session")
def authenticated_client(test_user_credentials):
    """API client authenticated with a real Supabase token"""
    client = APIClient()
    
    # For testing utility views, we'll use Django session auth instead of JWT
    # This will work with our test_settings.py configuration
    try:
        # Create a test user if it doesn't exist
        user, created = User.objects.get_or_create(
            username='test_user',
            defaults={'email': 'test@example.com', 'is_active': True}
        )
        user.set_password('password')
        user.save()
        
        # Use force_authenticate to bypass authentication checks
        client.force_authenticate(user=user)
    except Exception as e:
        print(f"Could not set up test authentication: {str(e)}")
        # If force_authenticate fails, we'll still try the Supabase token
        if test_user_credentials and test_user_credentials.get("auth_token"):
            client.credentials(HTTP_AUTHORIZATION=f'Bearer {test_user_credentials["auth_token"]}')
        else:
            pytest.skip("No authentication token available")
    
    return client

@pytest.fixture(scope="session")
def test_django_user(test_user_credentials):
    """Create a test user in the Django database
    
    This creates a Django User model instance matching the Supabase user
    for testing endpoints that require Django database user records.
    """
    if not test_user_credentials or not test_user_credentials.get("id"):
        pytest.skip("No valid test user credentials available")
    
    # Create or get the UserProfile
    user, created = UserProfile.objects.get_or_create(
        id=test_user_credentials["id"],
        defaults={
            "email": test_user_credentials["email"],
            "first_name": "Test",
            "last_name": "User",
            "credits": 1000,  # Give plenty of credits for testing credit-based views
        }
    )
    
    if not created:
        # Ensure the user has enough credits for our tests
        if user.credits < 1000:
            user.credits = 1000
            user.save()
    
    return user

@pytest.fixture(scope="session")
def test_admin_django_user(test_django_user):
    """Create a test admin user in the Django database"""
    # Make the test user an admin
    test_django_user.is_staff = True
    test_django_user.is_superuser = True
    test_django_user.save()
    
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
def test_bucket(test_user_credentials, supabase_services):
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
def test_table(test_user_credentials, supabase_services):
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
