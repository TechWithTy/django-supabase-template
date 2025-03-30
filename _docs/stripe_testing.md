# Stripe Integration Testing Guide

## Introduction

This document provides guidelines and best practices for testing Stripe integration in the Django application. It highlights common issues encountered during testing and their solutions.

## Common Issues and Solutions

### 1. Mocking the Stripe Client

#### Issue
The application uses `get_stripe_client()` from `config.py` to obtain a Stripe client instance. When testing, we need to patch this function to return a mock client instead of a real one to avoid making actual API calls.

#### Solution
Properly patch the `get_stripe_client()` function in both the views and config modules:

```python
# In test setup
@classmethod
def setUpClass(cls):
    super().setUpClass()
    
    # Create a patching function that returns our mock client
    def patched_get_stripe_client():
        return MockStripeClient(settings.STRIPE_SECRET_KEY)
    
    # Apply the patch to both places where get_stripe_client is imported
    cls.view_patcher = patch('apps.stripe_home.views.get_stripe_client', patched_get_stripe_client)
    cls.view_patcher.start()
    cls.config_patcher = patch('apps.stripe_home.config.get_stripe_client', patched_get_stripe_client)
    cls.config_patcher.start()

@classmethod
def tearDownClass(cls):
    # Stop the patchers
    cls.view_patcher.stop()
    cls.config_patcher.stop()
    super().tearDownClass()
```

### 2. Mock Implementation Structure

#### Issue
The Stripe client has a nested structure (e.g., `stripe_client.checkout.sessions.create()`), which needs to be properly reflected in the mock implementation.

#### Solution
Ensure your mock objects mirror the nested structure of the real Stripe client:

```python
class MockCheckoutService:
    def __init__(self):
        self.sessions = MockCheckoutSessionService()

class MockCheckoutSessionService:
    def create(self, **kwargs):
        # Implement mock behavior
        return MockCheckoutSession(**kwargs)

class MockStripeClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.checkout = MockCheckoutService()
        # Add other services as needed
```

### 3. Configuration Variables in Tests

#### Issue
The application might use settings variables (like `settings.BASE_URL`) that aren't defined in the test environment.

#### Solution
Modify the code to handle missing settings gracefully, or provide these settings in the test environment:

```python
# In the application code
default_success_url = f"{getattr(settings, 'BASE_URL', 'https://example.com')}/success"

# Or in the test
@override_settings(BASE_URL='https://test.example.com')
def test_something():
    # Test implementation
```

Another approach is to make your code accept parameters for these URLs:

```python
def _create_checkout_session(self, plan, user, success_url=None, cancel_url=None):
    # Use provided URLs or fall back to defaults
    default_success_url = f"{getattr(settings, 'BASE_URL', 'https://example.com')}/success"
    success_url = success_url or default_success_url
```

## Best Practices for Stripe Testing

1. **Use Test Mode Keys**: Always use Stripe test mode keys for testing (`sk_test_...`).

2. **Complete Mocking**: Ensure all Stripe API calls are properly mocked in tests.

3. **Test Edge Cases**: Test various scenarios including successful payments, failed payments, subscription cancellations, etc.

4. **Clean Up**: Clean up any test resources created during tests in the `tearDown` method.

5. **Consistent Mock Data**: Use consistent mock data across tests to make test failures easier to debug.

6. **Check Error Responses**: Verify that your code handles Stripe errors gracefully.

7. **Test Webhooks**: If you're using Stripe webhooks, test the webhook handling code with mock event data.

8. **Mock Response Structure**: Ensure your mock objects return response data with the same structure as the actual Stripe API.

## Conclusion

Properly testing Stripe integration requires careful mocking of the Stripe client and handling of configuration variables. By following the patterns and best practices outlined in this document, you can create robust tests for your Stripe integration that don't depend on the actual Stripe API.
