import os
import sys
import django
import pytest
from pathlib import Path
from utils.sensitive import load_environment_files
from apps.supabase_home.tests._verify_supabase_connection import run_verification
import uuid

# Add the backend directory to the Python path
backend_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Load environment variables
load_environment_files()

# Set up Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# Initialize Django
django.setup()

def pytest_addoption(parser):
    """Add command-line options to pytest"""
    parser.addoption(
        "--integration", 
        action="store_true", 
        default=False,
        help="Run integration tests that connect to real Supabase services"
    )

# Run verification before tests begin
def pytest_configure(config):
    """Run Supabase connection verification before tests begin"""
    print("Verifying Supabase connection before running tests...")
    success = run_verification()
    if not success:
        print("Supabase connection verification failed! Tests may not work correctly.")
        print("Please check your .env file and Supabase configuration.")
    
    # Set environment variable based on --integration flag
    if config.getoption("--integration"):
        os.environ["SKIP_INTEGRATION_TESTS"] = "false"
        print("Integration tests enabled - will connect to real Supabase services")
    else:
        os.environ["SKIP_INTEGRATION_TESTS"] = "true"
        print("Integration tests disabled - only running mock tests")

# The pytest_plugins declaration has been moved to the root conftest.py file

@pytest.fixture(scope="session")
def supabase_client():
    """Fixture to provide a real Supabase client for tests"""
    from apps.supabase_home.client import get_supabase_client
    return get_supabase_client()

@pytest.fixture(scope="session")
def supabase_service():
    """Fixture to provide a Supabase service for tests"""
    from apps.supabase_home.service import SupabaseService
    return SupabaseService()

@pytest.fixture(scope="session")
def test_user_credentials():
    """Test user credentials - configure in .env file"""
    return {
        "email": os.getenv("TEST_USER_EMAIL", "test@example.com"),
        "password": os.getenv("TEST_USER_PASSWORD", "testpassword123"),
    }

@pytest.fixture(scope="session")
def test_bucket_name():
    """Get test bucket name from environment or generate a unique one"""
    return os.getenv("TEST_BUCKET_NAME", f"test-bucket-{uuid.uuid4()}")

@pytest.fixture(scope="session")
def test_table_name():
    """Get test table name from environment or generate a unique one"""
    return os.getenv("TEST_TABLE_NAME", f"test_table_{uuid.uuid4().hex[:8]}")

@pytest.fixture(scope="session")
def check_supabase_resources():
    """Check if required Supabase resources exist and print diagnostic information"""
    from apps.supabase_home.auth import SupabaseAuthService
    from apps.supabase_home.storage import SupabaseStorageService
    from apps.supabase_home.database import SupabaseDatabaseService
    
    if os.getenv("SKIP_INTEGRATION_TESTS", "true").lower() == "true":
        return
    
    # Get bucket and table names for checking
    test_bucket_name = os.getenv("TEST_BUCKET_NAME", f"test-bucket-{uuid.uuid4()}")
    test_table_name = os.getenv("TEST_TABLE_NAME", f"test_table_{uuid.uuid4().hex[:8]}")
    
    print("\n============= SUPABASE INTEGRATION TEST DIAGNOSTICS ==============")
    
    # Check authentication
    auth_service = SupabaseAuthService()
    try:
        print("\nChecking authentication...")
        # Try public endpoint to verify connection
        auth_service._make_request("GET", "/auth/v1/settings")
        print("✓ Successfully connected to Supabase Auth API")
    except Exception as e:
        print(f"✗ Failed to connect to Supabase Auth API: {str(e)}")
    
    # Check storage service
    storage_service = SupabaseStorageService()
    try:
        print("\nChecking storage service...")
        # First try to authenticate
        auth_token = None
        if os.getenv("TEST_USER_EMAIL") and os.getenv("TEST_USER_PASSWORD"):
            try:
                print(f"  Signing in with test user: {os.getenv('TEST_USER_EMAIL')}")
                signin_result = auth_service.sign_in_with_email(
                    email=os.getenv("TEST_USER_EMAIL"),
                    password=os.getenv("TEST_USER_PASSWORD")
                )
                auth_token = signin_result.get("access_token")
                print("  ✓ Successfully signed in with test user")
            except Exception as e:
                print(f"  ✗ Failed to sign in with test user: {str(e)}")
        
        # Try to list buckets
        try:
            print(f"  Trying to list storage buckets (with auth token: {bool(auth_token)})")
            buckets = storage_service.list_buckets(auth_token=auth_token, is_admin=True)
            print(f"  ✓ Successfully listed buckets: {len(buckets)} found")
            
            if buckets:
                print(f"  Available buckets: {', '.join([b.get('name', 'unknown') for b in buckets])}")
            
            # Check if test bucket exists
            bucket_exists = any(b.get('name') == test_bucket_name for b in buckets)
            if bucket_exists:
                print(f"  ✓ Test bucket '{test_bucket_name}' exists")
            else:
                print(f"  ✗ Test bucket '{test_bucket_name}' does not exist")
        except Exception as e:
            print(f"  ✗ Failed to list buckets: {str(e)}")
    except Exception as e:
        print(f"✗ Storage service check failed: {str(e)}")
    
    # Check database service
    database_service = SupabaseDatabaseService()
    try:
        print("\nChecking database service...")
        try:
            # Try to list all tables
            print(f"  Trying to list tables (with auth token: {bool(auth_token)})")
            tables_query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            tables = database_service.execute_sql(tables_query, auth_token=auth_token)
            
            if tables:
                table_names = [t.get('table_name') for t in tables]
                print(f"  ✓ Successfully listed tables: {len(tables)} found")
                print(f"  Available tables: {', '.join(table_names)}")
                
                # Check if test table exists
                table_exists = test_table_name in table_names
                if table_exists:
                    print(f"  ✓ Test table '{test_table_name}' exists")
                else:
                    print(f"  ✗ Test table '{test_table_name}' does not exist")
                    
                    # Suggest SQL to create test table
                    print("\nTo create the test table, run this SQL in your Supabase SQL editor:")
                    print(f"""CREATE TABLE public.{test_table_name} (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    file_url TEXT,
    user_id UUID,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ
);""")
                    print("\nAnd enable row-level security and add policies:")
                    print(f"""ALTER TABLE public.{test_table_name} ENABLE ROW LEVEL SECURITY;""")
                    print(f"""CREATE POLICY "{test_table_name}_all_policy" ON public.{test_table_name}
    USING (true) WITH CHECK (true);""")
            else:
                print("  ✗ No tables found or no permission to list tables")
        except Exception as e:
            print(f"  ✗ Failed to list tables: {str(e)}")
    except Exception as e:
        print(f"✗ Database service check failed: {str(e)}")
    
    print("\n============= END DIAGNOSTICS =============\n")
    return True

@pytest.fixture(scope="session")
def integration_test(request):
    """Fixture to check if integration tests should run"""
    return request.config.getoption("--integration")
