import pytest
import os
import uuid
from datetime import datetime
import random
import string

from ..database import SupabaseDatabaseService
from ..init import get_supabase_client


class TestRealSupabaseDatabaseService:
    """
    Real-world integration tests for SupabaseDatabaseService
    
    These tests make actual API calls to Supabase and require:
    1. A valid Supabase URL and API keys in env variables
    2. Use of the --integration flag when running tests
    3. A test table must exist in your Supabase instance
    """
    
    @pytest.fixture
    def supabase_client(self):
        """Initialize and return the Supabase client"""
        try:
            return get_supabase_client()
        except Exception as e:
            raise Exception(f"Failed to initialize Supabase client: {str(e)}")
    
    @pytest.fixture
    def db_service(self):
        """Create a real SupabaseDatabaseService instance"""
        return SupabaseDatabaseService()
    
    @pytest.fixture
    def auth_token(self, supabase_client):
        """Get authentication token by signing in with test credentials or create a new user"""
        test_email = os.getenv("TEST_USER_EMAIL")
        test_password = os.getenv("TEST_USER_PASSWORD")
        
        if not test_email or not test_password:
            # Generate random credentials for a new test user
            random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            test_email = f"test_user_{random_suffix}@example.com"
            test_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            
            try:
                # Create a new user
                signup_response = supabase_client.auth.sign_up({
                    "email": test_email,
                    "password": test_password
                })
                print(f"Created test user: {test_email}")
                return signup_response.session.access_token
            except Exception as e:
                # If user already exists, try to sign in
                try:
                    auth_response = supabase_client.auth.sign_in_with_password({
                        "email": test_email,
                        "password": test_password
                    })
                    return auth_response.session.access_token
                except Exception as signin_error:
                    raise Exception(f"Failed to create or sign in test user: {str(e)} / {str(signin_error)}")
        
        try:
            # Sign in with provided test credentials
            auth_response = supabase_client.auth.sign_in_with_password({
                "email": test_email,
                "password": test_password
            })
            return auth_response.session.access_token
        except Exception as e:
            raise Exception(f"Failed to authenticate test user: {str(e)}")
    
    @pytest.fixture
    def test_table_name(self):
        """Get test table name from environment or use default with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return os.getenv("TEST_TABLE_NAME", f"test_table_{timestamp}")
    
    @pytest.fixture
    def test_record(self):
        """Generate a test record with a unique name"""
        unique_id = str(uuid.uuid4())
        return {
            "name": f"Test Item {unique_id}",
            "description": "Created by automated test"
        }
    
    def should_run_integration_tests(self):
        """Check if integration tests should run"""
        if os.getenv("SKIP_INTEGRATION_TESTS", "true").lower() == "true":
            return False
            
        if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_ANON_KEY"):
            return False
            
        return True
    
    def test_initialize_client(self, supabase_client):
        """Test that Supabase client initializes correctly"""

        assert supabase_client is not None
        # Verify client has required components
        assert hasattr(supabase_client, "auth")
        assert hasattr(supabase_client, "table")
    
    def test_create_and_delete_test_table(self, db_service, test_table_name, auth_token):
        """Test creating and deleting a test table"""
       
            
        try:
            # Create test table with admin privileges
            create_result = db_service.create_test_table(
                table=test_table_name,
                auth_token=auth_token,
                is_admin=True
            )
            
            assert create_result is not None
            
            # Delete the test table
            delete_result = db_service.delete_table(
                table=test_table_name,
                auth_token=auth_token,
                is_admin=True
            )
            
            assert delete_result is not None
            
        except Exception as e:
            pytest.fail(f"Table creation/deletion test failed: {str(e)}")
    
    def test_database_crud_operations(self, db_service, test_table_name, test_record, auth_token):
        """Test CRUD operations with a real Supabase database"""
    
            
        try:
            # First create the test table
            db_service.create_test_table(
                table=test_table_name,
                auth_token=auth_token,
                is_admin=True
            )
            
            # 1. Insert test data with authentication
            insert_result = db_service.insert_data(
                table=test_table_name,
                data=test_record,
                auth_token=auth_token
            )
            
            assert insert_result is not None
            assert len(insert_result) > 0
            assert "id" in insert_result[0]
            assert insert_result[0]["name"] == test_record["name"]
            
            # Store the ID for subsequent operations
            record_id = insert_result[0]["id"]
            
            # 2. Fetch the inserted data with authentication
            fetch_result = db_service.fetch_data(
                table=test_table_name,
                filters={"id": record_id},
                auth_token=auth_token
            )
            
            assert fetch_result is not None
            assert len(fetch_result) == 1
            assert fetch_result[0]["id"] == record_id
            assert fetch_result[0]["name"] == test_record["name"]
            
            # 3. Update the data with authentication
            updated_data = {"description": "Updated by automated test"}
            update_result = db_service.update_data(
                table=test_table_name,
                data=updated_data,
                filters={"id": record_id},
                auth_token=auth_token
            )
            
            assert update_result is not None
            assert len(update_result) == 1
            assert update_result[0]["id"] == record_id
            assert update_result[0]["description"] == updated_data["description"]
            
            # 4. Delete the test data to clean up with authentication
            delete_result = db_service.delete_data(
                table=test_table_name,
                filters={"id": record_id},
                auth_token=auth_token
            )
            
            assert delete_result is not None
            assert len(delete_result) == 1
            assert delete_result[0]["id"] == record_id
            
            # 5. Verify deletion by attempting to fetch
            empty_result = db_service.fetch_data(
                table=test_table_name,
                filters={"id": record_id},
                auth_token=auth_token
            )
            
            assert len(empty_result) == 0
            
            # Clean up by dropping the test table
            db_service.delete_table(
                table=test_table_name,
                auth_token=auth_token,
                is_admin=True
            )
            
        except Exception as e:
            # Clean up the test table even if the test fails
            try:
                db_service.delete_table(
                    table=test_table_name,
                    auth_token=auth_token,
                    is_admin=True
                )
            except Exception:
                pass  # Ignore cleanup errors
                
            pytest.fail(f"Database CRUD test failed: {str(e)}")
    
    def test_upsert_operation(self, db_service, test_table_name, test_record, auth_token):
        """Test the upsert operation with a real Supabase database"""

        try:
            # First create the test table
            db_service.create_test_table(
                table=test_table_name,
                auth_token=auth_token,
                is_admin=True
            )
            
            # 1. Insert test data with authentication
            insert_result = db_service.insert_data(
                table=test_table_name,
                data=test_record,
                auth_token=auth_token
            )
            
            record_id = insert_result[0]["id"]
            
            # 2. Upsert the same record with modified data
            upsert_data = {
                "id": record_id,
                "name": test_record["name"],
                "description": "Updated via upsert"
            }
            
            upsert_result = db_service.upsert_data(
                table=test_table_name,
                data=upsert_data,
                auth_token=auth_token
            )
            
            assert upsert_result is not None
            assert len(upsert_result) > 0
            assert upsert_result[0]["id"] == record_id
            assert upsert_result[0]["description"] == "Updated via upsert"
            
            # Clean up by dropping the test table
            db_service.delete_table(
                table=test_table_name,
                auth_token=auth_token,
                is_admin=True
            )
            
        except Exception as e:
            # Clean up the test table even if the test fails
            try:
                db_service.delete_table(
                    table=test_table_name,
                    auth_token=auth_token,
                    is_admin=True
                )
            except Exception:
                pass  # Ignore cleanup errors
                
            pytest.fail(f"Upsert test failed: {str(e)}")
    
    def test_call_function(self, db_service, auth_token):
        """Test calling a PostgreSQL function"""
        
        try:
            # Create a simple function to test with
            create_function_sql = """
            CREATE OR REPLACE FUNCTION test_function()
            RETURNS TEXT AS $$
            BEGIN
                RETURN 'Test function executed successfully';
            END;
            $$ LANGUAGE plpgsql;
            """
            
            # First create the function using exec_sql
            db_service._make_request(
                method="POST",
                endpoint="/rest/v1/rpc/exec_sql",
                auth_token=auth_token,
                is_admin=True,
                data={"query": create_function_sql}
            )
            
            # Now call the function we just created
            result = db_service.call_function(
                function_name="test_function",
                auth_token=auth_token
            )
            
            assert result is not None
            assert isinstance(result, str)
            assert "successfully" in result
            
        except Exception as e:
            pytest.fail(f"Function call test failed: {str(e)}")
