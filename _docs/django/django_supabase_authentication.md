# Supabase Authentication Guide

## Overview

This document provides a comprehensive guide on how to implement Supabase authentication in both test environments and production applications within the Django-Supabase template. It covers authentication mechanisms, JWT token handling, and best practices for secure API interactions.

## Table of Contents

1. [Authentication Flow](#authentication-flow)
2. [JWT Token Structure](#jwt-token-structure)
3. [Testing with Supabase Authentication](#testing-with-supabase-authentication)
4. [Real API Authentication](#real-api-authentication)
5. [Troubleshooting Common Issues](#troubleshooting-common-issues)

## Authentication Flow

The Django-Supabase template uses JWT (JSON Web Token) for authentication. Here's the typical flow:

1. **User Login**: User provides credentials to Supabase Auth service
2. **Token Generation**: Supabase generates a JWT token upon successful authentication
3. **Token Storage**: Token is stored client-side (localStorage, secure cookie, etc.)
4. **API Requests**: Token is included in subsequent API requests
5. **Token Validation**: Django backend validates the token using the Supabase JWT secret
6. **Access Control**: Resources are served based on the user's permissions in the token

## JWT Token Structure

Supabase JWT tokens contain several important claims:

```json
{
  "iss": "https://<project-ref>.supabase.co/auth/v1",  // Issuer
  "sub": "user-uuid",                                // Subject (User ID)
  "aud": "authenticated",                            // Audience
  "exp": 1743209788,                                 // Expiration time
  "iat": 1743206188,                                 // Issued at time
  "email": "user@example.com",                       // User email
  "app_metadata": {                                  // App metadata
    "provider": "email",
    "providers": ["email"]
  },
  "user_metadata": {                                 // User metadata
    "email_verified": true,
    "name": "User Name"
  },
  "role": "authenticated"                            // User role
}
```

## Testing with Supabase Authentication

### Setting Up Test Authentication

The template includes a `CustomAuthentication` class in `conftest.py` that simplifies authentication in tests:

```python
class CustomAuthentication(BaseAuthentication):
    def authenticate(self, request):
        # Get token from Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return None
            
        # Extract the token
        token = auth_header.split(' ')[1]
        
        try:
            # Decode and verify the token with relaxed validation for testing
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=['HS256'],
                options={
                    'verify_signature': True,
                    'verify_iat': False,  # Skip 'issued at' verification for testing
                    'verify_aud': False   # Skip audience verification for testing
                }
            )
            
            # Get or create user based on Supabase user ID
            user_id = payload.get('sub')
            if not user_id:
                raise AuthenticationFailed('Invalid token payload')
            
            # Create or get the user
            try:
                user = User.objects.get(username=user_id)
            except User.DoesNotExist:
                user = User.objects.create(
                    username=user_id,
                    email=payload.get('email', ''),
                    is_active=True
                )
            
            # Add Supabase claims to the user object
            user.supabase_claims = payload.get('claims', {})
            user.supabase_roles = payload.get('roles', [])
            
            return (user, payload)
            
        except Exception as e:
            logger.error(f"JWT validation error: {str(e)}")
            raise AuthenticationFailed('Authentication error')
```

### Creating Test Fixtures

Use the following fixtures in your tests to authenticate requests:

```python
@pytest.fixture
def test_user_credentials():
    """Return test user credentials for authentication."""
    return {
        "email": settings.TEST_USER_EMAIL,
        "password": settings.TEST_PASSWORD,
    }

@pytest.fixture
def authenticated_client(client, test_user_credentials):
    """Return an authenticated client for testing protected endpoints."""
    # Get auth token from Supabase
    auth_service = SupabaseAuthService()
    auth_data = auth_service.sign_in_with_password(test_user_credentials)
    auth_token = auth_data.get("access_token")
    
    # Create authenticated client
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {auth_token}")
    return client, auth_token
```

### Example Test Implementation

Here's how to use authentication in your tests:

```python
def test_list_files(authenticated_client):
    """Test listing files from a bucket."""
    client, auth_token = authenticated_client
    
    # Method 1: Using the token in the Authorization header (already set in the fixture)
    response = client.get(
        "/api/storage/files/",
        {"bucket_id": settings.TEST_BUCKET}
    )
    
    # Method 2: Passing the token in the request data
    response = client.post(
        "/api/storage/files/",
        {"bucket_id": settings.TEST_BUCKET, "auth_token": auth_token}
    )
    
    # Method 3: Using both approaches for maximum compatibility
    response = client.post(
        "/api/storage/files/",
        {"bucket_id": settings.TEST_BUCKET, "auth_token": auth_token}
    )
    
    assert response.status_code == 200
    assert "files" in response.data
```

### Debugging Authentication Issues

For debugging authentication problems, create a dedicated test method:

```python
def test_auth_debugging(authenticated_client):
    """Debug authentication issues with detailed logging."""
    client, auth_token = authenticated_client
    
    # Log token information
    print(f"Auth token available: {bool(auth_token)}")
    print(f"Auth token first 10 chars: {auth_token[:10]}...")
    
    # Test direct Supabase API call
    response = requests.get(
        f"{settings.SUPABASE_URL}/storage/v1/bucket",
        headers={
            "Authorization": f"Bearer {auth_token}",
            "apikey": settings.SUPABASE_ANON_KEY
        }
    )
    print(f"Direct API response status: {response.status_code}")
    print(response.json())
    
    # Test different authentication methods with your API
    # Method 1: Token in data
    response = client.post(
        "/api/storage/files/",
        {"bucket_id": "test-bucket", "auth_token": auth_token, "is_admin": True}
    )
    print(f"Auth endpoint (token in data) response status: {response.status_code}")
    print(f"Response data: {response.data}")
    
    # Method 2: Token in header
    response = client.post(
        "/api/storage/files/",
        {"bucket_id": "test-bucket", "is_admin": True}
    )
    print(f"Auth endpoint (token in header) response status: {response.status_code}")
    print(f"Response data: {response.data}")
```

## Real API Authentication

### Client-Side Implementation

In your frontend application, authenticate with Supabase and store the token:

```javascript
// Using Supabase JavaScript client
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  'https://your-project-ref.supabase.co',
  'your-anon-key'
)

// Sign in user
async function signIn(email, password) {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password
  })
  
  if (error) {
    console.error('Error signing in:', error.message)
    return null
  }
  
  // Store the session token
  return data.session.access_token
}

// Use token in API requests
async function fetchData(endpoint, token) {
  const response = await fetch(`/api/${endpoint}`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })
  
  return response.json()
}
```

### Server-Side Implementation

In your Django views, authenticate requests using the `SupabaseJWTAuthentication` class:

```python
@api_view(["GET", "POST"])
@authentication_classes([SupabaseJWTAuthentication])
@permission_classes([IsAuthenticated])
def list_files(request: Request) -> Response:
    """List files in a bucket."""
    # Extract parameters
    bucket_id = request.data.get("bucket_id") or request.query_params.get("bucket_id")
    path = request.data.get("path") or request.query_params.get("path", "")
    
    # Get auth token from request
    auth_token = _get_auth_token(request)
    
    # Use the token for Supabase API calls
    try:
        files = storage_service.list_files(
            bucket_id=bucket_id,
            path=path,
            auth_token=auth_token
        )
        return Response({"files": files}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
```

### Helper Function for Token Extraction

Use this helper function to extract the token from various places in the request:

```python
def _get_auth_token(request: Request) -> Optional[str]:
    """Extract auth token from request in various formats."""
    # Check if token is in request.auth (set by DRF authentication)
    if hasattr(request, 'auth') and request.auth:
        return request.auth
    
    # Check Authorization header
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    
    # Check request data
    auth_token = request.data.get('auth_token')
    if auth_token:
        return auth_token
    
    # Check query parameters
    auth_token = request.query_params.get('auth_token')
    if auth_token:
        return auth_token
    
    return None
```

## Troubleshooting Common Issues

### Invalid Token Errors

1. **"The token is not yet valid (iat)"**
   - **Cause**: The token's "issued at" time is in the future due to clock differences
   - **Solution**: Disable `verify_iat` in JWT validation options

2. **"Invalid audience"**
   - **Cause**: The token's audience claim doesn't match the expected value
   - **Solution**: Disable `verify_aud` in JWT validation options or ensure correct audience

3. **"Signature verification failed"**
   - **Cause**: Incorrect JWT secret or tampered token
   - **Solution**: Verify the `SUPABASE_JWT_SECRET` setting matches your project's JWT secret

### Authentication Flow Issues

1. **Token Not Found**
   - **Cause**: Token not being passed correctly in the request
   - **Solution**: Check all possible token locations (header, data, query params)

2. **User Not Created**
   - **Cause**: User creation failing during authentication
   - **Solution**: Add detailed logging in the authentication process

### Environment-Specific Issues

1. **Test Environment**
   - Use relaxed JWT validation (disable time and audience checks)
   - Ensure test user exists in Supabase
   - Set proper environment variables for test credentials

2. **Production Environment**
   - Use strict JWT validation
   - Implement proper token refresh mechanisms
   - Set appropriate token expiration times

## Best Practices

1. **Security**
   - Never expose JWT secrets in client-side code
   - Use HTTPS for all API communications
   - Implement token refresh mechanisms

2. **Testing**
   - Create dedicated test users in Supabase
   - Use environment variables for test credentials
   - Implement comprehensive authentication tests

3. **Error Handling**
   - Provide clear error messages for authentication failures
   - Log authentication errors with appropriate detail
   - Implement proper error responses for failed authentication
