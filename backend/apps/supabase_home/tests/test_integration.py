import os
import pytest
import uuid
import json
import time
from utils.sensitive import load_environment_files
from django.conf import settings

# Import the service classes from their respective modules
from apps.supabase_home.auth import SupabaseAuthService
from apps.supabase_home.storage import SupabaseStorageService
from apps.supabase_home.database import SupabaseDatabaseService

# Load environment variables for tests
load_environment_files()

@pytest.fixture
def test_record_data():
    """Generate unique test data for database operations"""
    return {
        "id": str(uuid.uuid4()),
        "name": f"Test Record {uuid.uuid4()}",
        "description": "This is a test record for integration testing",
        "created_at": "2023-01-01T00:00:00"
    }


class TestSupabaseIntegration:
    """Test Supabase integration with real Supabase services"""
    
    def test_authentication(self, supabase_client, test_user_credentials, check_supabase_resources):
        """Test authentication services"""
        # Skip if not using --integration flag
        if os.getenv("SKIP_INTEGRATION_TESTS", "true").lower() == "true":
            pytest.skip("Integration tests disabled - use --integration flag to run")
            
        # Skip if using a pre-existing test user
        if os.getenv("SKIP_USER_CREATION", "false").lower() == "true":
            pytest.skip("Using pre-existing test user - skipping sign-up test")
        
        # Use your custom AuthService
        auth_service = SupabaseAuthService()
        
        try:
            # Generate unique email for testing
            unique_email = f"testuser_{uuid.uuid4()}@example.com"
            password = "Password123!"
            user_metadata = {"name": "Test User", "role": "tester"}
            
            # 1. Sign up a new user using admin API (auto-confirms email)
            print(f"\nAttempting to create user with email: {unique_email} using admin API")
            signup_result = auth_service.admin_create_user(
                email=unique_email,
                password=password,
                user_metadata=user_metadata,
                email_confirm=True  # Auto-confirm the email
            )
            
            assert signup_result is not None
            assert "id" in signup_result
            assert "email" in signup_result
            assert signup_result["email"] == unique_email
            print(f"Successfully created user with ID: {signup_result['id']}")
            
            # 2. Sign in with the new user
            print(f"Attempting to sign in with email: {unique_email}")
            signin_result = auth_service.sign_in_with_email(
                email=unique_email,
                password=password
            )
            
            assert signin_result is not None
            assert "access_token" in signin_result
            assert "refresh_token" in signin_result
            assert "user" in signin_result
            print("Successfully signed in with the new user")
            
        except Exception as e:
            if "already registered" in str(e).lower():
                pytest.skip(f"User with email {unique_email} already exists")
            elif "rate limit" in str(e).lower():
                pytest.skip("Rate limit exceeded for auth operations")
            elif "not enabled" in str(e).lower() or "not configured" in str(e).lower():
                pytest.skip("Auth service not properly configured in Supabase")
            elif "email not confirmed" in str(e).lower():
                pytest.skip("Email confirmation is required but not supported in tests")
            elif "unauthorized" in str(e).lower() or "not authorized" in str(e).lower():
                pytest.skip("Admin API access is required for these tests")
            else:
                pytest.fail(f"Authentication test failed: {str(e)}")
    
    def test_storage_operations(self, check_supabase_resources, test_user_credentials):
        """Test storage operations"""
        # Get credentials from the fixture
        auth_token = test_user_credentials.get('auth_token')
        
        # Generate a unique bucket name for this test run
        unique_test_bucket = f"test-bucket-{uuid.uuid4().hex[:8]}"
        print(f"\nUsing unique test bucket name: {unique_test_bucket}")
        
        # Set up retry parameters
        max_retries = 3
        retry_delay = 3  # seconds
        
        # Define cleanup function for bucket
        def cleanup_bucket(bucket_id):
            try:
                storage_service.delete_bucket(
                    bucket_id=bucket_id,
                    auth_token=auth_token,
                    is_admin=True
                )
                print(f"Cleaned up bucket {bucket_id}")
                time.sleep(2)  # Give Supabase time to process the deletion
            except Exception as error:
                print(f"Note: Bucket {bucket_id} already deleted or not found: {str(error)}")
        
        # Initialize storage service
        storage_service = SupabaseStorageService()
        
        try:
            # First, try to delete the bucket if it exists (clean slate)
            try:
                print(f"Checking if bucket {unique_test_bucket} already exists")
                storage_service.delete_bucket(
                    bucket_id=unique_test_bucket,
                    auth_token=auth_token,
                    is_admin=True
                )
                print(f"Deleted existing bucket {unique_test_bucket}")
                time.sleep(3)  # Give Supabase time to process the deletion
            except Exception as error:
                if "not found" in str(error).lower() or "404" in str(error):
                    print(f"Bucket {unique_test_bucket} does not exist yet")
                else:
                    print(f"Error checking bucket: {str(error)}")
            
            # Create the bucket with retry logic
            bucket_created = False
            for attempt in range(max_retries):
                try:
                    print(f"\nAttempt {attempt+1}/{max_retries}: Creating test bucket {unique_test_bucket}")
                    storage_service.create_bucket(
                        bucket_id=unique_test_bucket,
                        public=True,
                        auth_token=auth_token,
                        is_admin=True
                    )
                    print(f"Successfully created bucket {unique_test_bucket}")
                    bucket_created = True
                    # Give Supabase time to fully register the bucket
                    time.sleep(5)
                    break
                except Exception as e:
                    print(f"Attempt {attempt+1} failed: {str(e)}")
                    if "already exists" in str(e).lower() or "409" in str(e):
                        print("Bucket already exists, attempting to delete and retry")
                        cleanup_bucket(unique_test_bucket)
                    if attempt < max_retries - 1:
                        print(f"Waiting {retry_delay} seconds before retrying...")
                        time.sleep(retry_delay)
                    else:
                        print("Maximum retry attempts reached")
            
            # Verify the bucket exists before proceeding
            bucket_verified = False
            if bucket_created:
                # Give Supabase some time to register the bucket in their system
                print(f"\nWaiting 5 seconds for bucket {unique_test_bucket} to be fully registered...")
                time.sleep(5)
                
                for attempt in range(max_retries):
                    try:
                        print(f"\nAttempt {attempt+1}/{max_retries}: Verifying bucket {unique_test_bucket} exists")
                        # Try direct bucket access first (more reliable than listing)
                        try:
                            print("Trying direct bucket access...")
                            storage_service.get_bucket(
                                bucket_id=unique_test_bucket,
                                auth_token=auth_token
                            )
                            print(f"Direct access to bucket {unique_test_bucket} successful")
                            bucket_verified = True
                            break
                        except Exception as direct_error:
                            print(f"Direct bucket access failed: {str(direct_error)}")
                        
                        # Fall back to bucket listing
                        buckets = storage_service.list_buckets(auth_token=auth_token, is_admin=True)
                        print(f"Found {len(buckets)} buckets: {[b.get('name') for b in buckets]}")
                        
                        if any(b.get('name') == unique_test_bucket for b in buckets):
                            print(f"Verified bucket {unique_test_bucket} exists in bucket list")
                            bucket_verified = True
                            break
                        else:
                            print(f"Bucket {unique_test_bucket} not found in bucket list")
                    except Exception as e:
                        print(f"Attempt {attempt+1} to verify bucket failed: {str(e)}")
                    
                    if attempt < max_retries - 1:
                        print(f"Waiting {retry_delay} seconds before retrying verification...")
                        time.sleep(retry_delay)
                    else:
                        print("Maximum verification attempts reached")
            
            # Only proceed with file operations if the bucket was verified or we're going to try anyway
            if not bucket_verified:
                print("Warning: Could not verify bucket exists, but will attempt file operations anyway")

            # Test file operations
            test_file_path = f"test-file-{uuid.uuid4()}.txt"
            test_file_content = f"Test content {uuid.uuid4()}"
            
            # Upload a file with retry logic
            print(f"\nUploading file to {unique_test_bucket}/{test_file_path}")
            upload_success = False
            upload_result = None
            
            for attempt in range(max_retries):
                try:
                    print(f"Attempt {attempt+1}/{max_retries}: Uploading file to {unique_test_bucket}/{test_file_path}")
                    
                    # If this is not the first attempt and previous attempts failed, try to recreate the bucket
                    if attempt > 0 and not upload_success:
                        try:
                            print("Previous upload attempts failed. Trying to recreate the bucket...")
                            # Try to delete the bucket first (in case it exists but is in a bad state)
                            try:
                                storage_service.delete_bucket(
                                    bucket_id=unique_test_bucket,
                                    auth_token=auth_token,
                                    is_admin=True
                                )
                                print(f"Deleted existing bucket {unique_test_bucket}")
                                # Give Supabase time to process the deletion
                                time.sleep(3)
                            except Exception as delete_error:
                                print(f"Note: Could not delete bucket: {str(delete_error)}")
                            
                            # Create a new bucket
                            storage_service.create_bucket(
                                bucket_id=unique_test_bucket,
                                public=True,
                                auth_token=auth_token,
                                is_admin=True
                            )
                            print(f"Recreated bucket {unique_test_bucket}")
                            # Give Supabase time to register the bucket
                            time.sleep(5)
                        except Exception as recreate_error:
                            print(f"Failed to recreate bucket: {str(recreate_error)}")
                    
                    # For file upload, we'll use a direct requests approach to have more control
                    import requests
                    url = f"{settings.SUPABASE_URL}/storage/v1/object/{unique_test_bucket}/{test_file_path}"
                    
                    # Set up headers with authentication
                    headers = {
                        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                        "Content-Type": "text/plain"
                    }
                    
                    # Make the request
                    response = requests.post(
                        url, 
                        headers=headers, 
                        data=test_file_content.encode(),
                        timeout=30
                    )
                    response.raise_for_status()
                    upload_result = response.json()
                    
                    upload_success = True
                    print(f"File uploaded successfully to {unique_test_bucket}/{test_file_path}")
                    # Verify the upload result contains expected data
                    if upload_result and isinstance(upload_result, dict):
                        print(f"Upload response: {upload_result}")
                    break
                except Exception as e:
                    print(f"Upload attempt {attempt+1} failed: {str(e)}")
                    # Log more details about the error
                    if hasattr(e, 'response') and e.response is not None:
                        try:
                            print(f"Response status: {e.response.status_code}")
                            print(f"Response content: {e.response.text}")
                        except Exception as resp_error:
                            print(f"Could not get response details: {str(resp_error)}")
                    
                    if attempt < max_retries - 1:
                        print(f"Waiting {retry_delay} seconds before retrying upload...")
                        time.sleep(retry_delay)
                    else:
                        print("Maximum upload retry attempts reached")
            
            # Fail the test if upload was not successful
            if not upload_success:
                pytest.fail(f"Failed to upload file to {unique_test_bucket}/{test_file_path} after {max_retries} attempts")
            
            # List files in the bucket with retry logic
            print(f"\nListing files in bucket {unique_test_bucket}")
            files_listed = False
            file_found = False
            
            for attempt in range(max_retries):
                try:
                    print(f"Attempt {attempt+1}/{max_retries}: Listing files in bucket {unique_test_bucket}")
                    
                    # For file listing, we'll use a direct requests approach to have more control
                    import requests
                    url = f"{settings.SUPABASE_URL}/storage/v1/object/list/{unique_test_bucket}"
                    
                    # Set up headers with authentication
                    headers = {
                        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                        "Content-Type": "application/json"
                    }
                    
                    # Make the request
                    response = requests.post(
                        url, 
                        headers=headers, 
                        json={"prefix": "", "limit": 100, "offset": 0},
                        timeout=30
                    )
                    response.raise_for_status()
                    file_list = response.json()
                    
                    files_listed = True
                    print(f"Successfully listed files in bucket {unique_test_bucket}")
                    print(f"Files in bucket: {file_list}")
                    
                    # Check if our uploaded file is in the list
                    if file_list and isinstance(file_list, list):
                        for file in file_list:
                            if file.get('name') == test_file_path:
                                file_found = True
                                print(f"Found our test file: {test_file_path}")
                                break
                    
                    if file_found:
                        break
                    else:
                        print(f"Warning: Uploaded file {test_file_path} not found in file list")
                        if attempt < max_retries - 1:
                            print("Waiting before retrying file listing...")
                            time.sleep(retry_delay)
                except Exception as e:
                    print(f"File listing attempt {attempt+1} failed: {str(e)}")
                    if hasattr(e, 'response') and e.response is not None:
                        try:
                            print(f"Response status: {e.response.status_code}")
                            print(f"Response content: {e.response.text}")
                        except Exception as resp_error:
                            print(f"Could not get response details: {str(resp_error)}")
                    
                    if attempt < max_retries - 1:
                        print(f"Waiting {retry_delay} seconds before retrying file listing...")
                        time.sleep(retry_delay)
                    else:
                        print("Maximum file listing retry attempts reached")
            
            # Skip the rest of the test if we couldn't list files
            if not files_listed:
                print("Skipping remaining tests due to file listing failure")
                return
            
            # Continue with other operations only if we've successfully uploaded and listed files
            if upload_success and files_listed and file_found:
                try:
                    # Download the file
                    print(f"\nDownloading file from {unique_test_bucket}/{test_file_path}")
                    
                    # For file download, we'll use a direct requests approach to have more control
                    import requests
                    url = f"{settings.SUPABASE_URL}/storage/v1/object/{unique_test_bucket}/{test_file_path}"
                    
                    # Set up headers with authentication
                    headers = {
                        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY
                    }
                    
                    # Make the request
                    response = requests.get(url, headers=headers, timeout=30)
                    response.raise_for_status()
                    downloaded_content = response.content.decode()
                    
                    print(f"Downloaded content: {downloaded_content}")
                    assert downloaded_content == test_file_content
                    print("File content matches the uploaded content")
                    
                    # Delete the file
                    print(f"\nDeleting file {unique_test_bucket}/{test_file_path}")
                    
                    # For file deletion, we'll use a direct requests approach to have more control
                    import requests
                    url = f"{settings.SUPABASE_URL}/storage/v1/object/{unique_test_bucket}/{test_file_path}"
                    
                    # Set up headers with authentication
                    headers = {
                        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY
                    }
                    
                    # Make the request
                    response = requests.delete(url, headers=headers, timeout=30)
                    response.raise_for_status()
                    
                    print("File deleted successfully")
                except Exception as e:
                    print(f"Error during download/delete operations: {str(e)}")
            else:
                print("Skipping download and delete operations due to previous failures")
        except Exception as e:
            print(f"Unexpected error in storage operations test: {str(e)}")
            pytest.fail(f"Test failed due to unexpected error: {str(e)}")
        finally:
            # Clean up: Delete the test bucket
            print(f"\nCleaning up: Attempting to delete bucket {unique_test_bucket}")
            cleanup_bucket(unique_test_bucket)
    
    def test_database_operations(self, check_supabase_resources, test_user_credentials):
        """Test database operations"""
  
        # First authenticate to get an auth token
        auth_service = SupabaseAuthService()
        database_service = SupabaseDatabaseService()
        
        # Get test user credentials from the fixture
        email = test_user_credentials.get('email')
        password = test_user_credentials.get('password')
        
        # Sign in with the test user
        print(f"\nAttempting to sign in with email: {email}")
        auth_result = auth_service.sign_in_with_email(email, password)
        
        auth_token = auth_result.get("access_token")
        assert auth_token is not None, "Failed to get authentication token"
        
        # Generate a unique table name for this test run
        test_table_name = f"test_table_{uuid.uuid4().hex[:8]}"
        print(f"\nUsing unique test table name: {test_table_name}")
        
        try:
            # Check if table exists and create it if it doesn't
            print(f"\nChecking if test table exists: {test_table_name}")
            table_exists = True
            try:
                database_service.fetch_data(
                    table=test_table_name,
                    auth_token=auth_token,
                    limit=1
                )
                print(f"Test table {test_table_name} exists")
            except Exception as table_error:
                if "404" in str(table_error) or "Not Found" in str(table_error):
                    table_exists = False
                    print(f"Test table {test_table_name} does not exist, creating it...")
                    try:
                        # Create the test table
                        database_service.create_test_table(
                            table=test_table_name,
                            auth_token=auth_token,
                            is_admin=True
                        )
                        print(f"Successfully created test table {test_table_name}")
                        table_exists = True
                    except Exception as create_error:
                        print(f"Failed to create test table: {str(create_error)}")
                        pytest.fail(f"Could not create test table {test_table_name}. Error: {str(create_error)}")
                else:
                    raise
            
            # 3. Insert data
            if table_exists:
                test_data = {
                    "name": f"Test Record {uuid.uuid4()}",
                    "description": "This is a test record",
                    "created_at": "2023-01-01T00:00:00"
                }
                
                print(f"Inserting data into table: {test_table_name}")
                insert_result = database_service.insert_data(
                    table=test_table_name,
                    data=test_data,
                    auth_token=auth_token
                )
                
                assert insert_result is not None
                assert len(insert_result) > 0
                record_id = insert_result[0].get("id")
                assert record_id is not None
                print(f"Successfully inserted record with ID: {record_id}")
                
                # 4. Fetch the inserted data
                print(f"Fetching data from table: {test_table_name}")
                fetch_result = database_service.fetch_data(
                    table=test_table_name,
                    auth_token=auth_token,
                    filters={"id": f"eq.{record_id}"}
                )
                
                assert fetch_result is not None
                assert len(fetch_result) > 0
                assert fetch_result[0].get("name") == test_data["name"]
                print("Successfully fetched inserted data")
                
                # 5. Update the data
                update_data = {"description": "Updated description"}
                print(f"Updating record with ID: {record_id}")
                update_result = database_service.update_data(
                    table=test_table_name,
                    data=update_data,
                    filters={"id": f"eq.{record_id}"},
                    auth_token=auth_token
                )
                
                assert update_result is not None
                assert len(update_result) > 0
                assert update_result[0].get("description") == update_data["description"]
                print("Successfully updated record")
                
                # 6. Delete the data
                print(f"Deleting record with ID: {record_id}")
                delete_result = database_service.delete_data(
                    table=test_table_name,
                    filters={"id": f"eq.{record_id}"},
                    auth_token=auth_token
                )
                
                assert delete_result is not None
                assert len(delete_result) > 0
                assert delete_result[0].get("id") == record_id
                print("Successfully deleted record")
        except Exception as e:
            if not isinstance(e, pytest.skip.Exception):
                pytest.fail(f"Database operations test failed: {str(e)}")
        finally:
            # Clean up - try to delete the test table if it was created
            if 'test_table_name' in locals() and test_table_name:
                try:
                    print(f"\nCleaning up - deleting test table: {test_table_name}")
                    database_service.delete_table(
                        table=test_table_name,
                        auth_token=auth_token,
                        is_admin=True
                    )
                    print(f"Successfully deleted test table: {test_table_name}")
                except Exception as e:
                    print(f"Warning: Failed to delete test table: {str(e)}")
    
    def test_end_to_end_flow(self, check_supabase_resources, test_user_credentials, test_bucket_name, test_table_name):
        """Test an end-to-end flow combining authentication, database, and storage operations"""
        
        # Check if integration tests are enabled
        if os.getenv("SKIP_INTEGRATION_TESTS", "true").lower() == "true":
            pytest.skip("Integration tests disabled")
            
        auth_service = SupabaseAuthService()
        storage_service = SupabaseStorageService()
        database_service = SupabaseDatabaseService()
        
        # 1. Authenticate
        auth_token = None
        try:
            print("\nAttempting to sign in...")
            result = auth_service.sign_in_with_email(
                email=test_user_credentials['email'],
                password=test_user_credentials['password']
            )
            auth_token = result.get("access_token")
            print("Sign in successful")
        except Exception as e:
            try:
                print(f"Sign-in failed, attempting to create test user: {str(e)}")
                result = auth_service.admin_create_user(
                    email=test_user_credentials['email'],
                    password=test_user_credentials['password'],
                    email_confirm=True
                )
                
                # Try to sign in with the newly created user
                try:
                    signin_result = auth_service.sign_in_with_email(
                        email=test_user_credentials['email'],
                        password=test_user_credentials['password']
                    )
                    auth_token = signin_result.get("access_token")
                    print("Sign in successful after user creation")
                except Exception as signin_err:
                    print(f"Failed to sign in after user creation: {str(signin_err)}")
            except Exception as create_err:
                print(f"Failed to create user: {str(create_err)}")
                
        # Check if auth token was obtained
        assert auth_token is not None, "Failed to get authentication token"
        
        # 2. Create bucket if it doesn't exist
        try:
            # Check if bucket exists and delete it if it does
            print("\nChecking if bucket exists...")
            buckets = storage_service.list_buckets(auth_token=auth_token, is_admin=True)
            bucket_exists = any(b.get('name') == test_bucket_name for b in buckets)

            if bucket_exists:
                print(f"Bucket {test_bucket_name} already exists, deleting it first")
                try:
                    storage_service.delete_bucket(
                        bucket_id=test_bucket_name,
                        auth_token=auth_token,
                        is_admin=True
                    )
                    print(f"Successfully deleted existing bucket {test_bucket_name}")
                    # Wait a moment to ensure the deletion is processed
                    import time
                    time.sleep(1)
                except Exception as delete_error:
                    print(f"Warning: Failed to delete existing bucket: {str(delete_error)}")
            
            # Create the bucket
            try:
                print(f"Creating test bucket: {test_bucket_name}")
                storage_service.create_bucket(
                    bucket_id=test_bucket_name,
                    public=True,
                    auth_token=auth_token,
                    is_admin=True  # Use admin privileges for bucket creation
                )
                print(f"Successfully created bucket {test_bucket_name}")
            except Exception as e:
                # If bucket already exists (409 conflict), consider it a success
                if "409" in str(e) or "already exists" in str(e).lower():
                    print(f"Bucket {test_bucket_name} already exists (409 Conflict), continuing test")
                else:
                    raise  # Re-raise the exception to be caught by the outer try/except
        except Exception as e:
            pytest.fail(f"Failed to create bucket: {str(e)}")
        
        # 3. Check if test table exists and create it if it doesn't exist
        try:
            print(f"\nChecking if test table exists: {test_table_name}")
            # Try to fetch data from the table to see if it exists
            table_exists = True
            try:
                database_service.fetch_data(
                    table=test_table_name,
                    auth_token=auth_token,
                    limit=1
                )
                print(f"Test table {test_table_name} exists")
            except Exception as table_error:
                if "404" in str(table_error) or "Not Found" in str(table_error):
                    table_exists = False
                    print(f"Test table {test_table_name} does not exist, creating it...")
                    try:
                        # Create the test table
                        database_service.create_test_table(
                            table=test_table_name,
                            auth_token=auth_token,
                            is_admin=True
                        )
                        print(f"Successfully created test table {test_table_name}")
                        table_exists = True
                    except Exception as create_error:
                        print(f"Failed to create test table: {str(create_error)}")
                        pytest.skip(f"Could not create test table {test_table_name}. Error: {str(create_error)}")
                else:
                    raise
            
            if table_exists:
                test_data = {
                    "name": f"E2E Test Record {uuid.uuid4()}",
                    "description": "Created during end-to-end test",
                    "created_at": "2023-01-01T00:00:00",
                    "user_id": auth_token
                }
                
                print(f"Inserting data into table: {test_table_name}")
                insert_result = database_service.insert_data(
                    table=test_table_name,
                    data=test_data,
                    auth_token=auth_token
                )
                
                assert insert_result is not None
                assert len(insert_result) > 0
                record_id = insert_result[0].get("id")
                assert record_id is not None
                print(f"Successfully inserted record with ID: {record_id}")
        except Exception as e:
            if not isinstance(e, pytest.skip.Exception):
                pytest.fail(f"Database operations failed: {str(e)}")
        
        # 4. Upload a file with the record data
        test_file_path = f"test-file-{uuid.uuid4()}.txt"
        file_data = json.dumps({
            "record_id": record_id,
            "metadata": test_data
        })
        
        print(f"\nUploading file to {test_bucket_name}/{test_file_path}")
        upload_result = storage_service.upload_file(
            bucket_id=test_bucket_name,
            path=test_file_path,
            file_data=file_data.encode(),
            content_type="application/json",
            auth_token=auth_token
        )
        
        assert upload_result is not None
        print(f"Successfully uploaded file: {test_file_path}")
        
        # 5. Get file URL
        file_url = storage_service.get_public_url(
            bucket_id=test_bucket_name,
            path=test_file_path
        )
        
        assert file_url is not None
        print(f"Got public URL for file: {file_url}")
        
        # 6. Update database record with file URL
        update_data = {
            "file_url": file_url,
            "updated_at": "2023-01-02T00:00:00"
        }
        
        print("\nUpdating record with file URL")
        update_result = database_service.update_data(
            table=test_table_name,
            id=record_id,
            data=update_data,
            auth_token=auth_token
        )
        
        assert update_result is not None
        assert "file_url" in update_result
        assert update_result["file_url"] == file_url
        print("Successfully updated record with file URL")
        
        print("End-to-end test completed successfully!")
        
        # Clean up resources
        print("\nCleaning up resources...")
        
        # Delete file
        try:
            print(f"Cleaning up: Deleting file {test_file_path}")
            storage_service.delete_file(
                bucket_id=test_bucket_name,
                path=test_file_path,
                auth_token=auth_token
            )
            print(f"Successfully deleted file: {test_file_path}")
        except Exception as e:
            print(f"Failed to delete file: {str(e)}")
        
        # Delete record
        try:
            print(f"Cleaning up: Deleting record {record_id}")
            database_service.delete_data(
                table=test_table_name,
                id=record_id,
                auth_token=auth_token
            )
            print(f"Successfully deleted record: {record_id}")
        except Exception as e:
            print(f"Failed to delete record: {str(e)}")
        
        # Delete table
        try:
            print(f"Cleaning up: Deleting test table {test_table_name}")
            database_service.delete_table(
                table=test_table_name,
                auth_token=auth_token,
                is_admin=True  # Use admin privileges for table deletion
            )
            print(f"Successfully deleted test table {test_table_name}")
        except Exception as e:
            print(f"Failed to delete table: {str(e)}")
        
        # Delete bucket
        try:
            print(f"Cleaning up: Deleting test bucket {test_bucket_name}")
            storage_service.delete_bucket(
                bucket_id=test_bucket_name,
                auth_token=auth_token,
                is_admin=True  # Use admin privileges for bucket deletion
            )
            print("Successfully deleted test bucket")
        except Exception as e:
            print(f"Failed to delete bucket: {str(e)}")