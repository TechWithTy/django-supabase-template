# Django + Supabase Template API Documentation

## Authentication Endpoints

### Health Check
```
GET /api/health/
```
Checks if the API is running properly.

**Response:**
```json
{
  "status": "ok"
}
```

### Register
```
POST /api/register/
```
Registers a new user with Supabase.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response:**
```json
{
  "id": "user-uuid",
  "email": "user@example.com",
  "app_metadata": { ... },
  "user_metadata": { ... },
  "aud": "authenticated",
  "confirmation_sent_at": "2023-01-01T00:00:00Z"
}
```

### Login
```
POST /api/login/
```
Logs in a user and returns a JWT token.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "ey...",
  "user": {
    "id": "user-uuid",
    "email": "user@example.com"
  }
}
```

### Get User Info
```
GET /api/user/
```
Gets information about the authenticated user.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "id": 1,
  "username": "user-uuid",
  "email": "user@example.com",
  "supabase_id": "user-uuid",
  "roles": ["authenticated"],
  "claims": { ... },
  "supabase_data": { ... }
}
```

### Logout
```
POST /api/logout/
```
Logs out the current user.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

## User Management Endpoints

### List Users (Admin Only)
```
GET /api/users/
```
Lists all users (admin only).

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
[
  {
    "id": 1,
    "username": "user1-uuid",
    "email": "user1@example.com",
    "profile": {
      "supabase_uid": "user1-uuid",
      "subscription_tier": "free",
      "credits_balance": 100,
      "created_at": "2023-01-01T00:00:00Z",
      "updated_at": "2023-01-01T00:00:00Z"
    }
  },
  { ... }
]
```

### Get Current User
```
GET /api/users/me/
```
Gets the current user's information.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "id": 1,
  "username": "user-uuid",
  "email": "user@example.com",
  "profile": {
    "supabase_uid": "user-uuid",
    "subscription_tier": "free",
    "credits_balance": 100,
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  }
}
```

### Add Credits (Admin Only)
```
POST /api/users/{user_id}/add_credits/
```
Adds credits to a user's account (admin only).

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "amount": 100
}
```

**Response:**
```json
{
  "message": "Added 100 credits to user-uuid's account",
  "new_balance": 200
}
```

### List Supabase Users (Admin Only)
```
GET /api/users/supabase_users/
```
Lists all users from Supabase (admin only).

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
[
  {
    "id": "user1-uuid",
    "email": "user1@example.com",
    "app_metadata": { ... },
    "user_metadata": { ... },
    "created_at": "2023-01-01T00:00:00Z"
  },
  { ... }
]
```

## Credits Endpoints

### Get Credit Balance
```
GET /api/credits/
```
Gets the current user's credit balance.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "credits": 100,
  "subscription_tier": "free"
}
```

### List Credit Transactions
```
GET /api/credits/transactions/
```
Lists the current user's credit transactions.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
[
  {
    "id": 1,
    "username": "user-uuid",
    "amount": -1,
    "balance_after": 99,
    "description": "API request to /api/resource/",
    "endpoint": "/api/resource/",
    "created_at": "2023-01-01T00:00:00Z"
  },
  { ... }
]
```

### Get Credit Transaction Summary
```
GET /api/credits/transactions/summary/
```
Gets a summary of the current user's credit transactions.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "total_added": 100,
  "total_used": 10,
  "current_balance": 90
}
```

### List Credit Usage Rates
```
GET /api/credits/rates/
```
Lists the credit usage rates for different API endpoints.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
[
  {
    "id": 1,
    "endpoint_path": "/api/resource/",
    "credits_per_request": 1,
    "description": "Standard API request",
    "is_active": true
  },
  { ... }
]
```

## Supabase Integration

This section documents the Supabase integration functions available in the Django + Supabase template. These functions allow you to interact with various Supabase services directly from your Django application.

### Database Operations

#### Fetch Data

Retrieve data from a Supabase table with optional filtering, ordering, and pagination.

```python
from apps.supabase.client import supabase

# Basic fetch
data = supabase.database.fetch_data(
    table='table_name',
    auth_token='user_jwt_token',  # Optional
    select='*',                   # Default: '*'
    filters={'column': 'value'},  # Optional
    order='column.asc',           # Optional
    limit=10,                     # Optional
    offset=0                      # Optional
)
```

#### Insert Data

Insert one or more records into a Supabase table.

```python
from apps.supabase.client import supabase

# Insert a single record
data = supabase.database.insert_data(
    table='table_name',
    data={'column1': 'value1', 'column2': 'value2'},
    auth_token='user_jwt_token'  # Optional
)

# Insert multiple records
data = supabase.database.insert_data(
    table='table_name',
    data=[
        {'column1': 'value1', 'column2': 'value2'},
        {'column1': 'value3', 'column2': 'value4'}
    ],
    auth_token='user_jwt_token'  # Optional
)
```

#### Update Data

Update records in a Supabase table that match the specified filters.

```python
from apps.supabase.client import supabase

data = supabase.database.update_data(
    table='table_name',
    data={'column1': 'new_value'},
    filters={'id': 123},
    auth_token='user_jwt_token'  # Optional
)
```

#### Upsert Data

Insert or update records in a Supabase table.

```python
from apps.supabase.client import supabase

data = supabase.database.upsert_data(
    table='table_name',
    data={'id': 123, 'column1': 'value1', 'column2': 'value2'},
    auth_token='user_jwt_token'  # Optional
)
```

#### Delete Data

Delete records from a Supabase table that match the specified filters.

```python
from apps.supabase.client import supabase

data = supabase.database.delete_data(
    table='table_name',
    filters={'id': 123},
    auth_token='user_jwt_token'  # Optional
)
```

#### Call a Postgres Function

Call a PostgreSQL function defined in your Supabase database.

```python
from apps.supabase.client import supabase

result = supabase.database.call_function(
    function_name='my_function',
    params={'param1': 'value1', 'param2': 'value2'},
    auth_token='user_jwt_token'  # Optional
)
```

### Auth

#### Overview

The Auth service provides methods for user management, authentication, and session handling using Supabase Auth.

#### Create a New User

Create a new user with email and password.

```python
from apps.supabase.client import supabase

user = supabase.auth.create_user(
    email='user@example.com',
    password='secure_password',
    user_metadata={'name': 'John Doe'}  # Optional
)
```

#### Create an Anonymous User

Create an anonymous user.

```python
from apps.supabase.client import supabase

session = supabase.auth.create_anonymous_user()
```

#### Sign In a User

Sign in a user with email and password.

```python
from apps.supabase.client import supabase

session = supabase.auth.sign_in_with_email(
    email='user@example.com',
    password='secure_password'
)
```

#### Sign In with ID Token

Sign in a user with an ID token from a third-party provider.

```python
from apps.supabase.client import supabase

session = supabase.auth.sign_in_with_id_token(
    provider='google',
    id_token='google_id_token'
)
```

#### Sign In a User through OTP

Send a one-time password to the user's email.

```python
from apps.supabase.client import supabase

result = supabase.auth.sign_in_with_otp(
    email='user@example.com'
)
```

#### Verify and Log In through OTP

Verify a one-time password and log in the user.

```python
from apps.supabase.client import supabase

session = supabase.auth.verify_otp(
    email='user@example.com',
    token='otp_token',
    type='email'  # Default: 'email'
)
```

#### Sign In a User through OAuth

Get the URL to redirect the user for OAuth sign-in.

```python
from apps.supabase.client import supabase

redirect_info = supabase.auth.sign_in_with_oauth(
    provider='google',
    redirect_url='https://example.com/auth/callback'
)
```

#### Sign In a User through SSO

Sign in a user through SSO with a domain.

```python
from apps.supabase.client import supabase

redirect_info = supabase.auth.sign_in_with_sso(
    domain='example.com',
    redirect_url='https://example.com/auth/callback'
)
```

#### Sign Out a User

Sign out a user.

```python
from apps.supabase.client import supabase

result = supabase.auth.sign_out(
    auth_token='user_jwt_token'
)
```

#### Send a Password Reset Request

Send a password reset email to the user.

```python
from apps.supabase.client import supabase

result = supabase.auth.reset_password(
    email='user@example.com',
    redirect_url='https://example.com/reset-password'  # Optional
)
```

#### Retrieve a Session

Retrieve the user's session.

```python
from apps.supabase.client import supabase

session = supabase.auth.get_session(
    auth_token='user_jwt_token'
)
```

#### Retrieve a New Session

Refresh the user's session with a refresh token.

```python
from apps.supabase.client import supabase

new_session = supabase.auth.refresh_session(
    refresh_token='refresh_token'
)
```

#### Retrieve a User

Retrieve a user by ID (admin only).

```python
from apps.supabase.client import supabase

user = supabase.auth.get_user(
    user_id='user_id'
)
```

#### Update a User

Update a user's data (admin only).

```python
from apps.supabase.client import supabase

updated_user = supabase.auth.update_user(
    user_id='user_id',
    user_data={
        'email': 'new_email@example.com',
        'user_metadata': {'name': 'New Name'}
    }
)
```

#### Retrieve Identities Linked to a User

Retrieve identities linked to a user (admin only).

```python
from apps.supabase.client import supabase

identities = supabase.auth.get_user_identities(
    user_id='user_id'
)
```

#### Link an Identity to a User

Link an identity to a user.

```python
from apps.supabase.client import supabase

result = supabase.auth.link_identity(
    auth_token='user_jwt_token',
    provider='github',
    redirect_url='https://example.com/auth/callback'
)
```

#### Unlink an Identity from a User

Unlink an identity from a user.

```python
from apps.supabase.client import supabase

result = supabase.auth.unlink_identity(
    auth_token='user_jwt_token',
    identity_id='identity_id'
)
```

#### Set the Session Data

Set the session data.

```python
from apps.supabase.client import supabase

result = supabase.auth.set_session_data(
    auth_token='user_jwt_token',
    data={'key': 'value'}
)
```

#### Exchange an Auth Code for a Session

This is handled automatically by the OAuth callback process.

### Auth MFA

#### Enroll a Factor

Enroll a multi-factor authentication factor.

```python
from apps.supabase.client import supabase

factor = supabase.auth.enroll_mfa_factor(
    auth_token='user_jwt_token',
    factor_type='totp'  # Default: 'totp'
)
```

#### Create a Challenge

Create a multi-factor authentication challenge.

```python
from apps.supabase.client import supabase

challenge = supabase.auth.create_mfa_challenge(
    auth_token='user_jwt_token',
    factor_id='factor_id'
)
```

#### Verify a Challenge

Verify a multi-factor authentication challenge.

```python
from apps.supabase.client import supabase

result = supabase.auth.verify_mfa_challenge(
    auth_token='user_jwt_token',
    factor_id='factor_id',
    challenge_id='challenge_id',
    code='verification_code'
)
```

#### Unenroll a Factor

Unenroll a multi-factor authentication factor.

```python
from apps.supabase.client import supabase

result = supabase.auth.unenroll_mfa_factor(
    auth_token='user_jwt_token',
    factor_id='factor_id'
)
```

### Edge Functions

#### Invoke a Supabase Edge Function

Invoke a Supabase Edge Function.

```python
from apps.supabase.client import supabase

result = supabase.edge_functions.invoke_function(
    function_name='my_function',
    invoke_method='POST',  # Default: 'POST'
    body={'param1': 'value1'},  # Optional
    headers={'Custom-Header': 'value'},  # Optional
    auth_token='user_jwt_token'  # Optional
)
```

### Realtime

#### Subscribe to Channel

Subscribe to a Realtime channel.

```python
from apps.supabase.client import supabase

subscription = supabase.realtime.subscribe_to_channel(
    channel='my_channel',
    event='*',  # Default: '*' for all events
    auth_token='user_jwt_token'  # Optional
)
```

#### Unsubscribe from a Channel

Unsubscribe from a Realtime channel.

```python
from apps.supabase.client import supabase

result = supabase.realtime.unsubscribe_from_channel(
    subscription_id='subscription_id',
    auth_token='user_jwt_token'  # Optional
)
```

#### Unsubscribe from All Channels

Unsubscribe from all Realtime channels.

```python
from apps.supabase.client import supabase

result = supabase.realtime.unsubscribe_all(
    auth_token='user_jwt_token'  # Optional
)
```

#### Retrieve All Channels

Retrieve all subscribed channels.

```python
from apps.supabase.client import supabase

channels = supabase.realtime.get_channels(
    auth_token='user_jwt_token'  # Optional
)
```

#### Broadcast a Message

Broadcast a message to a channel.

```python
from apps.supabase.client import supabase

result = supabase.realtime.broadcast_message(
    channel='my_channel',
    event='my_event',
    payload={'message': 'Hello, world!'},
    auth_token='user_jwt_token'  # Optional
)
```

### Storage

#### Create a Bucket

Create a new storage bucket.

```python
from apps.supabase.client import supabase

bucket = supabase.storage.create_bucket(
    bucket_id='my_bucket',
    public=False,  # Default: False
    file_size_limit=10485760,  # Optional: 10MB in bytes
    allowed_mime_types=['image/jpeg', 'image/png'],  # Optional
    auth_token='user_jwt_token'  # Optional
)
```

#### Retrieve a Bucket

Retrieve a bucket by ID.

```python
from apps.supabase.client import supabase

bucket = supabase.storage.get_bucket(
    bucket_id='my_bucket',
    auth_token='user_jwt_token'  # Optional
)
```

#### List All Buckets

List all buckets.

```python
from apps.supabase.client import supabase

buckets = supabase.storage.list_buckets(
    auth_token='user_jwt_token'  # Optional
)
```

#### Update a Bucket

Update a bucket.

```python
from apps.supabase.client import supabase

bucket = supabase.storage.update_bucket(
    bucket_id='my_bucket',
    public=True,  # Optional
    file_size_limit=20971520,  # Optional: 20MB in bytes
    allowed_mime_types=['image/jpeg', 'image/png', 'application/pdf'],  # Optional
    auth_token='user_jwt_token'  # Optional
)
```

#### Delete a Bucket

Delete a bucket.

```python
from apps.supabase.client import supabase

result = supabase.storage.delete_bucket(
    bucket_id='my_bucket',
    auth_token='user_jwt_token'  # Optional
)
```

#### Empty a Bucket

Empty a bucket (delete all files).

```python
from apps.supabase.client import supabase

result = supabase.storage.empty_bucket(
    bucket_id='my_bucket',
    auth_token='user_jwt_token'  # Optional
)
```

#### Upload a File

Upload a file to a bucket.

```python
from apps.supabase.client import supabase

# Upload from bytes
with open('path/to/file.jpg', 'rb') as f:
    file_data = f.read()
    
result = supabase.storage.upload_file(
    bucket_id='my_bucket',
    path='folder/file.jpg',
    file_data=file_data,
    content_type='image/jpeg',  # Optional
    auth_token='user_jwt_token'  # Optional
)

# Upload from file-like object
with open('path/to/file.jpg', 'rb') as f:
    result = supabase.storage.upload_file(
        bucket_id='my_bucket',
        path='folder/file.jpg',
        file_data=f,
        content_type='image/jpeg',  # Optional
        auth_token='user_jwt_token'  # Optional
    )
```

#### Download a File

Download a file from a bucket.

```python
from apps.supabase.client import supabase

file_data = supabase.storage.download_file(
    bucket_id='my_bucket',
    path='folder/file.jpg',
    auth_token='user_jwt_token'  # Optional
)

# Save to disk
with open('downloaded_file.jpg', 'wb') as f:
    f.write(file_data)
```

#### List All Files in a Bucket

List files in a bucket.

```python
from apps.supabase.client import supabase

files = supabase.storage.list_files(
    bucket_id='my_bucket',
    path='folder/',  # Optional: filter by path prefix
    limit=100,  # Default: 100
    offset=0,  # Default: 0
    sort_by={'column': 'name', 'order': 'asc'},  # Optional
    auth_token='user_jwt_token'  # Optional
)
```

#### Move an Existing File

Move a file to a new location.

```python
from apps.supabase.client import supabase

result = supabase.storage.move_file(
    bucket_id='my_bucket',
    source_path='folder/file.jpg',
    destination_path='new_folder/file.jpg',
    auth_token='user_jwt_token'  # Optional
)
```

#### Copy an Existing File

Copy a file to a new location.

```python
from apps.supabase.client import supabase

result = supabase.storage.copy_file(
    bucket_id='my_bucket',
    source_path='folder/file.jpg',
    destination_path='new_folder/file_copy.jpg',
    auth_token='user_jwt_token'  # Optional
)
```

#### Delete Files in a Bucket

Delete files from a bucket.

```python
from apps.supabase.client import supabase

# Delete a single file
result = supabase.storage.delete_file(
    bucket_id='my_bucket',
    paths='folder/file.jpg',
    auth_token='user_jwt_token'  # Optional
)

# Delete multiple files
result = supabase.storage.delete_file(
    bucket_id='my_bucket',
    paths=['folder/file1.jpg', 'folder/file2.jpg'],
    auth_token='user_jwt_token'  # Optional
)
```

#### Create a Signed URL

Create a signed URL for a file.

```python
from apps.supabase.client import supabase

signed_url = supabase.storage.create_signed_url(
    bucket_id='my_bucket',
    path='folder/file.jpg',
    expires_in=60,  # Default: 60 seconds
    auth_token='user_jwt_token'  # Optional
)
```

#### Create Signed URLs

Create signed URLs for multiple files.

```python
from apps.supabase.client import supabase

signed_urls = supabase.storage.create_signed_urls(
    bucket_id='my_bucket',
    paths=['folder/file1.jpg', 'folder/file2.jpg'],
    expires_in=60,  # Default: 60 seconds
    auth_token='user_jwt_token'  # Optional
)
```

#### Create Signed Upload URL

Create a signed URL for uploading a file.

```python
from apps.supabase.client import supabase

signed_upload_url = supabase.storage.create_signed_upload_url(
    bucket_id='my_bucket',
    path='folder/file.jpg',
    auth_token='user_jwt_token'  # Optional
)
```

#### Upload to a Signed URL

Upload a file to a signed URL.

```python
from apps.supabase.client import supabase

# Get a signed upload URL
signed_upload_data = supabase.storage.create_signed_upload_url(
    bucket_id='my_bucket',
    path='folder/file.jpg',
    auth_token='user_jwt_token'
)

# Upload to the signed URL
with open('path/to/file.jpg', 'rb') as f:
    supabase.storage.upload_to_signed_url(
        signed_url=signed_upload_data['url'],
        file_data=f.read(),
        content_type='image/jpeg'  # Optional
    )
```

#### Retrieve Public URL

Get the public URL for a file in a public bucket.

```python
from apps.supabase.client import supabase

public_url = supabase.storage.get_public_url(
    bucket_id='my_bucket',
    path='folder/file.jpg'
)
```

## Rate Limiting

The API implements rate limiting based on the user's subscription tier:

- **Anonymous**: 100 requests per day
- **Free**: 100 requests per day
- **Basic**: 1,000 requests per day
- **Premium**: 5,000 requests per day
- **Enterprise**: 10,000 requests per day

When a rate limit is exceeded, the API will return a 429 Too Many Requests response:

```json
{
  "detail": "Request limit exceeded. Try again later."
}
```

## Credit-Based Usage

Certain API endpoints require credits to use. The number of credits required per request is defined in the CreditUsageRate model and can be viewed using the `/api/credits/rates/` endpoint.

If a user doesn't have enough credits for an operation, the API will return a 403 Forbidden response:

```json
{
  "detail": "Insufficient credits for this operation."
}
