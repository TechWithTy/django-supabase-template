# Credit-Based Views Documentation

## Overview

This document provides detailed information about the credit-based view system implemented in the Django Supabase Template. The credit-based view system allows you to restrict access to specific API endpoints based on the user's credit balance, ensuring that users can only access premium features if they have sufficient credits.

## Table of Contents

1. [Architecture](#architecture)
2. [Available Components](#available-components)
3. [Usage Examples](#usage-examples)
4. [Implementation Details](#implementation-details)
5. [API Reference](#api-reference)

## Architecture

The credit-based view system is built on top of Django REST Framework and consists of several components:

- **Credit Script View**: A dedicated view for executing the `main.py` script with credit-based access control
- **Credit Decorator**: A decorator that can be applied to any view function to add credit-based access control
- **Credit Utility Function**: A utility function that can wrap any existing view function with credit-based access control

All components interact with the `UserProfile` model to check and update the user's credit balance and record transactions in the `CreditTransaction` model.

## Available Components

### 1. Main Script Execution View

Location: `backend/apps/users/views/creditable_views/main_view.py`

This view provides an API endpoint for executing the `main.py` script in the root directory with credit-based access control. The script execution requires a configurable number of credits (default: 5) which are deducted from the user's account upon successful execution.

### 2. Credit Decorator

Location: `backend/apps/users/views/creditable_views/credit_script_view.py`

The `with_credits` decorator can be applied to any view function to add credit-based access control. The decorator checks if the user has sufficient credits before executing the function and deducts the credits upon successful execution.

### 3. Credit Utility Function

Location: `backend/apps/users/views/creditable_views/utility_view.py`

The `call_function_with_credits` utility function can wrap any existing view function with credit-based access control without modifying the original function. This provides a non-intrusive way to add credit requirements to existing functions.

## Usage Examples

### 1. Using the Main Script Execution View

```python
# In urls.py
from backend.apps.users.views.creditable_views.credit_script_view import credit_script_view

urlpatterns = [
    # ...
    path('script/run/', credit_script_view.execute_main_script, name='run_main_script'),
    # ...
]
```

API Request:
```json
POST /api/script/run/
{
    "parameters": {
        "input_file": "data.csv",
        "mode": "process"
    }
}
```

Admin API Request with credit override:
```json
POST /api/script/run/
{
    "parameters": {
        "input_file": "data.csv",
        "mode": "process"
    },
    "credit_amount": 10
}
```

### 2. Using the Credit Decorator

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from backend.apps.users.views.creditable_views.credit_script_view import with_credits

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@with_credits(credit_amount=10)
def process_data(request):
    # Expensive data processing logic
    return Response({"status": "success", "data": processed_data})
```

### 3. Using the Credit Utility Function

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from backend.apps.users.views.creditable_views.utility_view import call_function_with_credits

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_report(request):
    def report_generator(req):
        # Complex report generation logic
        return Response({"report": "generated data"})
    
    return call_function_with_credits(report_generator, request, credit_amount=20)
```

## Implementation Details

### Credit Verification Process

1. The user makes a request to a credit-based endpoint
2. The system checks if the user is authenticated
3. If the user is an admin, they can override the credit amount
4. The system retrieves the user's profile and checks if they have sufficient credits
5. If the user has sufficient credits, the function is executed
6. Upon successful execution, the credits are deducted from the user's account and a transaction is recorded
7. The response includes credit usage information

### Error Handling

The credit-based view system provides detailed error responses with appropriate HTTP status codes:

- **401 Unauthorized**: If the user is not authenticated
- **402 Payment Required**: If the user has insufficient credits
- **400 Bad Request**: If the credit amount is invalid
- **500 Internal Server Error**: If there's an error retrieving the user profile or executing the function

## API Reference

### Main Script Execution View

**Endpoint**: `/api/script/run/`

**Method**: POST

**Authentication**: Required

**Request Body**:
```json
{
    "parameters": {
        "param1": "value1",
        "param2": "value2"
    },
    "credit_amount": 10 // Optional, admin only
}
```

**Response**:
```json
{
    "success": true,
    "exit_code": 0,
    "stdout": "Output from the script",
    "stderr": "",
    "credits_used": 5,
    "credits_remaining": 95,
    "result": {} // Parsed JSON if available
}
```

### Credit Decorator

**Function Signature**:
```python
def with_credits(credit_amount: int = 5):
    # Implementation
```

**Parameters**:
- `credit_amount`: Number of credits required to execute the function (default: 5)

### Credit Utility Function

**Function Signature**:
```python
def call_function_with_credits(func: Callable[[Request], Response], 
                              request: Request, 
                              credit_amount: int = 5) -> Response:
    # Implementation
```

**Parameters**:
- `func`: The function to call (must accept a Request object as its first parameter)
- `request`: The request object to pass to the function
- `credit_amount`: Number of credits required to execute the function (default: 5)

**Returns**:
- The response from the function, with credit information added
