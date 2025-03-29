# Supabase Testing Guide

## Table of Contents

1. [Testing Django Endpoints with Supabase Integration](#testing-django-endpoints-with-supabase-integration)
2. [Authentication Setup](#authentication-setup)
3. [Realtime API Testing](#realtime-api-testing)
4. [Common Issues](#common-issues)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)

## Testing Django Endpoints with Supabase Integration

### Setting Up Tests for Django Views with Supabase

When testing Django views that interact with Supabase services, follow these guidelines:

1. **Use Fixtures**: Leverage pytest fixtures to set up authentication, test data, and service instances.

2. **Test the Full Request-Response Cycle**:

   Ensure you test the complete flow from Django view to Supabase and back:

   ```python
   def test_my_endpoint(self, authenticated_client, test_user_credentials):
       # Make a request to your Django endpoint
       url = reverse('my_app:my_endpoint')
       response = authenticated_client.post(url, data={'key': 'value'}, format='json')
       
       # Assert the response is as expected
       assert response.status_code == 200
       assert 'expected_key' in response.data
   ```

3. **Clean Up After Tests**: Always implement proper teardown to clean up any resources created during tests.

### Testing with Supabase Authentication

When testing any Supabase endpoints that require authentication, there are several common issues and solutions to be aware of:

#### 1. Authentication Token Handling

Ensure your authentication token is properly set in the request headers:

```python
# In your test client setup
client.credentials(HTTP_AUTHORIZATION=f'Bearer {auth_token}')

# When making direct requests
headers = {
    'Authorization': f'Bearer {auth_token}',
    'apikey': settings.SUPABASE_KEY
}
```

#### 2. Debugging Authentication Issues

If you encounter 401 or 403 errors, implement a debugging test to verify your authentication setup:

```python
def test_auth_debugging(self, authenticated_client, test_user_credentials):
    """Debug authentication issues."""
    self.logger.info("=== AUTHENTICATION DEBUGGING TEST ====")
    self.logger.info(f"Auth token available: {bool(test_user_credentials['auth_token'])}")
    if test_user_credentials['auth_token']:
        self.logger.info(f"Auth token first 20 chars: {test_user_credentials['auth_token'][:20]}...")
    
    # Check if the authenticated_client has the auth token in its credentials
    self.logger.info(f"Authenticated client credentials: {authenticated_client.credentials}")
    
    # Make a simple request to verify authentication
    url = reverse('users:get_channels')
    response = authenticated_client.get(url)
    
    self.logger.info(f"Test request status code: {response.status_code}")
    if hasattr(response, 'data'):
        self.logger.info(f"Test request response data: {response.data}")
```

#### 3. Common Authentication Fixes

Based on our debugging experiences, here are key fixes for authentication issues:

- **Verify Token Format**: Ensure the token is properly formatted with the 'Bearer ' prefix
- **Check Token Expiration**: Supabase tokens typically expire after 1 hour; generate fresh tokens for tests
- **Inspect Request Headers**: Use logging to verify headers are correctly set in each request
- **Validate Environment Variables**: Ensure `SUPABASE_URL` and `SUPABASE_KEY` are correctly set

```python
# Verify environment variables are set correctly
def test_environment_setup(self):
    self.logger.info(f"SUPABASE_URL set: {bool(settings.SUPABASE_URL)}")
    self.logger.info(f"SUPABASE_KEY set: {bool(settings.SUPABASE_KEY)}")
    if settings.SUPABASE_URL:
        self.logger.info(f"SUPABASE_URL format: {settings.SUPABASE_URL[:10]}...")
```

#### 4. Parameter Naming for Realtime Endpoints

When testing Supabase Realtime endpoints specifically, pay special attention to parameter names in your requests:

```python
# CORRECT parameter naming for subscribe_to_channel
data = {
    "channel": "my-channel-name",  # Use "channel" not "name"
    "config": {"broadcast": {"self": True}, "private": True}
}

# CORRECT parameter naming for unsubscribe_from_channel
data = {
    "subscription_id": channel_id  # Use "subscription_id" not "channel_id"
}

# CORRECT parameter naming for broadcast_message
data = {
    "channel": channel_name,  # Use "channel" not "channel_id"
    "event": "my-event",
    "payload": {"message": "Hello World"}
}
```

**Common Mistake**: Using incorrect parameter names like "name" instead of "channel" or "channel_id" instead of "subscription_id" will result in 403 authentication errors, even when your authentication token is valid. This happens because the view expects specific parameter names to extract and process the data correctly.

#### 5. Debugging Authentication Flow

To thoroughly debug authentication issues, implement a test that traces the complete authentication flow:

```python
def test_complete_auth_flow(self, test_user_credentials, supabase_services):
    """Test the complete authentication flow from login to API access."""
    # 1. Verify credentials
    self.logger.info(f"Test user email: {test_user_credentials['email']}")
    
    # 2. Attempt direct login with Supabase
    try:
        auth_service = supabase_services['auth']
        login_result = auth_service.sign_in(
            email=test_user_credentials['email'],
            password=test_user_credentials['password']
        )
        self.logger.info(f"Direct login successful: {bool(login_result)}")
        
        # 3. Extract and verify token
        new_token = login_result.get('access_token')
        self.logger.info(f"New token obtained: {bool(new_token)}")
        
        # 4. Test token with a direct API call
        from rest_framework.test import APIClient
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_token}')
        
        # 5. Make test request
        url = reverse('users:get_channels')
        response = client.get(url)
        self.logger.info(f"Test request with new token - status: {response.status_code}")
    except Exception as e:
        self.logger.error(f"Authentication flow test failed: {str(e)}")
```

## Realtime API Testing

### Setting Up Supabase Realtime API Tests

Testing the Supabase Realtime API requires special attention to both authentication and Row Level Security (RLS) policies. Here's a comprehensive guide:

#### 1. Required RLS Policies

Before your tests will work, you must set up these RLS policies in your Supabase project:

```sql
-- Enable RLS on the realtime.messages table if not already enabled
ALTER TABLE IF EXISTS realtime.messages ENABLE ROW LEVEL SECURITY;

-- Policy 1: Allow authenticated users to receive broadcasts
CREATE POLICY "Allow authenticated users to receive broadcasts" 
ON realtime.messages
FOR SELECT
TO authenticated
USING (true);

-- Policy 2: Allow authenticated users to send broadcasts
CREATE POLICY "Allow authenticated users to send broadcasts" 
ON realtime.messages
FOR INSERT
TO authenticated
WITH CHECK (true);

-- Policy 3: Allow authenticated users to use presence
CREATE POLICY "Allow authenticated users to use presence" 
ON realtime.messages
FOR SELECT
TO authenticated
USING (true);
```

#### 2. Test Settings Configuration

Ensure your `test_settings.py` file includes the correct authentication classes:

```python
# Override REST_FRAMEWORK settings for testing
# Make sure to include the SupabaseJWTAuthentication class
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.authentication.authentication.SupabaseJWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

# Ensure the Supabase JWT middleware is included
if 'apps.authentication.middleware.SupabaseJWTMiddleware' not in MIDDLEWARE:
    MIDDLEWARE.append('apps.authentication.middleware.SupabaseJWTMiddleware')
```

#### 3. View Configuration

All views that interact with Realtime API must explicitly include the authentication class:

```python
@api_view(["POST"])
@authentication_classes([SupabaseJWTAuthentication])  # This line is critical
@permission_classes([permissions.IsAuthenticated])
def subscribe_to_channel(request: Request) -> Response:
    # View implementation
    ...
```

#### 4. Test Implementation

When writing tests for Realtime endpoints, always:

1. **Explicitly set the auth token in requests**:

```python
response = authenticated_client.post(
    url, 
    data, 
    format='json',
    HTTP_AUTHORIZATION=f'Bearer {self.auth_token}'  # Explicitly set token
)
```

2. **Use private channels with proper configuration**:

```python
data = {
    "channel": channel_name,
    "config": {"broadcast": {"self": True}, "private": True}  # private: True is required
}
```

3. **Handle both authentication errors and Supabase API errors**:

```python
try:
    # Make request
    response = authenticated_client.post(...)
    
    # Check for both 401/403 (auth issues) and 500 (API issues)
    if response.status_code in [401, 403]:
        self.logger.error(f"Authentication error: {response.content}")
    elif response.status_code >= 500:
        self.logger.error(f"Supabase API error: {response.content}")
        
    # Assert expected response
    assert response.status_code == status.HTTP_201_CREATED
    
except Exception as e:
    self.logger.error(f"Test failed with exception: {str(e)}")
    pytest.fail(f"Failed to create channel: {str(e)}")
```

#### 5. Troubleshooting Realtime API 403 Errors

If you're getting 403 errors from the Supabase Realtime API (not from Django), check:

1. **RLS Policies**: Ensure the RLS policies above are correctly set up in your Supabase project
2. **JWT Secret**: Verify your `SUPABASE_JWT_SECRET` is correctly set
3. **Service Role**: For admin operations, ensure you're using the service role key
4. **Channel Configuration**: Make sure you're setting `private: True` in channel config
5. **Direct API Test**: Try a direct API call to isolate if it's a Django or Supabase issue:

```python
def test_direct_realtime_api(self, test_user_credentials):
    """Test direct API call to Supabase Realtime."""
    import requests
    
    url = f"{settings.SUPABASE_URL}/realtime/v1/subscribe"
    headers = {
        'Content-Type': 'application/json',
        'apikey': settings.SUPABASE_KEY,
        'Authorization': f'Bearer {test_user_credentials["auth_token"]}'
    }
    data = {
        'channel': f'test-direct-{uuid.uuid4().hex[:8]}',
        'event': '*',
        'config': {'private': True}
    }
    
    response = requests.post(url, json=data, headers=headers)
    self.logger.info(f"Direct API status: {response.status_code}")
    self.logger.info(f"Direct API response: {response.text}")
```

## Authentication Setup

### Prerequisites

- A Supabase project with Storage enabled
- Django project with Supabase integration
- Pytest for running tests

### Setting Up Test Users

For tests that require authentication, you'll need to create test users with valid authentication tokens. Here's how to set this up:

```python
# In your conftest.py or test fixture file
import pytest
from apps.supabase_home.auth import SupabaseAuthService

@pytest.fixture
def test_user_credentials():
    """Create a test user and return credentials."""
    # Initialize auth service
    auth_service = SupabaseAuthService(
        base_url=settings.SUPABASE_URL,
        api_key=settings.SUPABASE_KEY
    )
```

## Common Issues

### 1. Authentication Errors (401, 403)

If you're getting 401 or 403 errors in your tests, check the following:

- Make sure your test is using the `authenticated_client` fixture
- Check if the token has expired (Supabase tokens typically last 1 hour)
- Verify the token is correctly formatted
- Make sure you're using the correct parameter names in your request data
- Ensure the authentication classes are correctly configured in test_settings.py
- Verify that your views explicitly include the authentication class decorator

### 2. Storage API Endpoint Format Issues

When testing Storage API endpoints, ensure you're using the correct format for paths:

```python
# CORRECT: No leading slash in path
path = "folder/file.txt"  

# INCORRECT: Leading slash will cause errors
path = "/folder/file.txt"  # This will fail
```

### 3. Database API Query Issues

When testing Database API endpoints, ensure your queries are correctly formatted:

```python
# CORRECT: Use proper column names and operators
query = {
    "column": "name",
    "operator": "eq",
    "value": "test"
}

# INCORRECT: Using wrong operator format
query = {
    "column": "name",
    "operator": "=",  # Should be "eq"
    "value": "test"
}
```

## Best Practices

### 1. Use Fixtures for Common Setup

Leverage pytest fixtures for common setup tasks:

```python
@pytest.fixture(scope="function")
def test_bucket(authenticated_client, test_user_credentials):
    """Create a test bucket for storage tests."""
    bucket_name = f"test-bucket-{uuid.uuid4().hex[:8]}"
    
    # Create the bucket
    url = reverse('users:create_bucket')
    response = authenticated_client.post(
        url, 
        {"bucket_id": bucket_name, "public": True},
        format='json'
    )
    
    # Skip if bucket creation fails
    if response.status_code != 201:
        pytest.skip(f"Failed to create test bucket: {response.content}")
        return None
        
    yield bucket_name
    
    # Clean up the bucket after tests
    delete_url = reverse('users:delete_bucket')
    authenticated_client.delete(f"{delete_url}?bucket_id={bucket_name}")
```

### 2. Implement Proper Teardown

Always clean up resources created during tests:

```python
def tearDown(self):
    """Clean up after test case."""
    # Clean up any test channels that were created
    if hasattr(self, 'test_channels') and self.test_channels:
        for channel_id in self.test_channels:
            try:
                # Unsubscribe from the channel
                self.realtime_service.unsubscribe_from_channel(
                    subscription_id=channel_id,
                    auth_token=self.auth_token
                )
            except Exception as e:
                self.logger.warning(f"Failed to clean up test channel {channel_id}: {str(e)}")
```

### 3. Use Descriptive Test Names

Name your tests descriptively to make it clear what they're testing:

```python
def test_create_bucket_with_valid_params(self, authenticated_client):
    """Test creating a bucket with valid parameters."""
    # Test implementation

def test_create_bucket_with_invalid_params(self, authenticated_client):
    """Test creating a bucket with invalid parameters."""
    # Test implementation
```

## Troubleshooting

### Common Error Messages and Solutions

#### 1. "Authentication credentials were not provided"

**Solution**:
- Check if you're using the `authenticated_client` fixture
- Verify the token is correctly set in the request headers
- Ensure your view has the `@authentication_classes([SupabaseJWTAuthentication])` decorator
- Check if the token has expired

#### 2. "Failed to connect to Supabase API"

**Solution**:
- Verify your `SUPABASE_URL` is correct
- Check if your Supabase project is online
- Ensure your network allows connections to the Supabase API

#### 3. "Permission denied" or "Access denied" from Supabase API

**Solution**:
- Check if your RLS policies are correctly set up
- Verify you're using the correct API key (anon vs service role)
- Ensure the authenticated user has the necessary permissions

#### 4. "Invalid token" or "Token expired"

**Solution**:
- Generate a fresh token for your tests
- Check if your `SUPABASE_JWT_SECRET` is correctly set
- Verify the token format and expiration time
