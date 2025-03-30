# Stripe Integration Test Troubleshooting Guide

## Common Testing Issues and Solutions

This document outlines common issues encountered when testing the Stripe integration and provides solutions to resolve them.

## Table of Contents
1. [App Registration Issues](#app-registration-issues)
2. [Database Table Naming](#database-table-naming)
3. [Import Path Problems](#import-path-problems)
4. [Migration Issues](#migration-issues)
5. [Model Field Name Mismatches](#model-field-name-mismatches)
6. [URL Resolution Issues](#url-resolution-issues)
7. [Testing Strategy](#testing-strategy)
8. [Django ORM Relation Mocking Issues](#django-orm-relation-mocking-issues)
9. [Stripe API Client Patching Issues](#stripe-api-client-patching-issues)
10. [True End-to-End Testing vs. Mocking](#true-end-to-end-testing-vs-mocking)

## App Registration Issues

### Problem: Model Not Found in INSTALLED_APPS

Error message similar to:
```
RuntimeError: Model class stripe_home.models.StripeCustomer doesn't declare an explicit app_label and isn't in an application in INSTALLED_APPS.
```

### Solution:

1. Ensure the app is properly registered in `settings.py`:
   ```python
   LOCAL_APPS = [
       # ...
       "apps.stripe_home",  # Full Python path to the app
   ]
   ```

2. Check the app's `apps.py` configuration:
   ```python
   class StripeHomeConfig(AppConfig):
       name = 'apps.stripe_home'  # Full Python path
       label = 'stripe_home'      # Database table prefix (no dots)
       verbose_name = 'Stripe Integration'
   ```

3. Register the app configuration in `__init__.py`:
   ```python
   default_app_config = 'apps.stripe_home.apps.StripeHomeConfig'
   ```

## Database Table Naming

### Problem: Conflicting Model Registration

Error message similar to:
```
RuntimeError: Conflicting 'stripecustomer' models in application 'stripe_home': <class 'apps.stripe_home.models.StripeCustomer'> and <class 'stripe_home.models.StripeCustomer'>.
```

Or SQLite errors about invalid table names:
```
sqlite3.OperationalError: no such table: apps.stripe_home_stripeplan
```

### Solution:

1. Make sure the `app_label` in model Meta classes matches the `label` in AppConfig:
   ```python
   class StripeCustomer(models.Model):
       # ...
       class Meta:
           app_label = 'stripe_home'  # Must match the label in AppConfig
   ```

2. Avoid using dots in app_label as SQLite doesn't support table names with dots.

## Import Path Problems

### Problem: Module Import Errors

This occurs when tests use relative imports but the app is registered with a different path.

### Solution:

1. Use absolute imports in test files:
   ```python
   # Instead of this:
   from ..models import StripeCustomer
   
   # Use this:
   from apps.stripe_home.models import StripeCustomer
   ```

2. Ensure your app signal imports in `apps.py` use the same import style:
   ```python
   # Use importlib.util.find_spec to safely check if the module exists
   if importlib.util.find_spec('apps.stripe_home.signals'):
       import apps.stripe_home.signals  # noqa
   ```

## Migration Issues

### Problem: Missing Tables in Test Database

Error message similar to:
```
django.db.utils.OperationalError: no such table: stripe_home_stripeplan
```

### Solution:

1. Make sure migrations are properly created for the app:
   ```bash
   python manage.py makemigrations stripe_home
   ```

2. For tests running with `--nomigrations`, ensure your tests include proper setup:
   ```python
   from django.db import connection
   
   # In setUp method
   with connection.schema_editor() as schema_editor:
       schema_editor.create_model(StripeCustomer)
       schema_editor.create_model(StripePlan)
   ```

3. Or remove the `--nomigrations` flag from pytest configuration in `pytest.ini` if you want migrations to run during tests.

## Model Field Name Mismatches

### Problem: Unexpected Keyword Arguments Error

Error message similar to:
```
TypeError: StripeSubscription() got unexpected keyword arguments: 'customer', 'plan'
```

### Solution:

1. Check your model definition for the correct field names:
   ```python
   # Look at the actual model definition in models.py
   # For example, the StripeSubscription model has fields like:  
   #  - user (not customer)
   #  - plan_id (not plan)
   ```

2. Update your test code to use the correct field names:
   ```python
   # Instead of this:
   db_subscription = StripeSubscription.objects.create(
       customer=stripe_customer,  # Wrong field name
       plan=self.db_plan,         # Wrong field name
       # ...
   )
   
   # Use this:
   db_subscription = StripeSubscription.objects.create(
       user=self.user,             # Correct field name
       plan_id=self.db_plan.plan_id, # Correct field name
       # ...
   )
   ```

3. Be aware that foreign key relationships might have different field names than the related model:
   - The model field could be named `user` but the related model is the User model
   - The model field could be `plan_id` but expects a string, not a Plan object

## URL Resolution Issues

### Problem: NoReverseMatch Error

Error message similar to:
```
django.urls.exceptions.NoReverseMatch: Reverse for 'customer-portal' not found. 'customer-portal' is not a valid view function or pattern name.
```

### Solution:

1. Check the URL configuration in your app's `urls.py` file for the correct name:
   ```python
   # In apps/stripe_home/urls.py
   path('customer-portal/', CustomerPortalView.as_view(), name='customer_portal')
   # Note: name is 'customer_portal' with underscore, not 'customer-portal' with hyphen
   ```

2. Verify if your app's URLs are included with a namespace in the main `urls.py`:
   ```python
   # In core/urls.py
   path('api/stripe/', include(('apps.stripe_home.urls', 'stripe'), namespace='stripe'))
   # Note: namespace is 'stripe', not 'stripe_home'
   ```

3. Update your reverse calls to use the correct name and namespace:
   ```python
   # Instead of this (incorrect):
   url = reverse('stripe:customer-portal')
   # or
   url = reverse('stripe_home:customer_portal')
   
   # Use this (correct):
   url = reverse('stripe:customer_portal')
   ```

4. For debugging URL resolution issues, try listing all available URLs:
   ```python
   from django.urls import get_resolver
   # Print all available URL names and patterns
   for url in get_resolver().reverse_dict.keys():
       if isinstance(url, str):
           print(url)
   ```

## Testing Strategy

### Best Practices for Stripe Integration Tests

1. **Use Stripe Test Mode**:
   - Always use Stripe's test API keys in your test environment
   - Utilize Stripe's test webhooks for event testing

2. **Test Data Management**:
   - Create dedicated test fixtures for Stripe models
   - Clean up test data in `tearDown` methods
   - Use transaction isolation (`TransactionTestCase`) for webhook tests

3. **Mock Stripe API Calls**:
   - For unit tests, consider mocking Stripe API responses
   - For integration tests, use real API calls with test keys

4. **Testing Webhooks**:
   - Use Stripe's webhook event constructors to simulate events
   - Test webhook signatures for security verification

### Example Test Case

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.stripe_home.models import StripeCustomer, StripePlan, StripeSubscription

User = get_user_model()

class StripeWebhookTest(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create test plan
        self.plan = StripePlan.objects.create(
            plan_id='price_test123',
            name='Test Plan',
            amount=1999,
            currency='usd',
            interval='month',
            initial_credits=100,
            monthly_credits=50,
            active=True,
            livemode=False
        )

    def test_subscription_created_webhook(self):
        # Test implementation
        pass

## Django ORM Relation Mocking Issues

### Problem: Cannot Assign Mock Objects to Django Relations

When writing tests that involve relationships between models (like OneToOneField), you might encounter errors like this when trying to use mock objects:

```
ValueError: Cannot assign "<MagicMock id='123456'>": "CustomUser.profile" must be a "UserProfile" instance.
```

### Solution:

1. **Create Real Instances Instead of Mocks**: For Django ORM relations, you need to create actual model instances rather than using mock objects:

```python
# WRONG - This will fail:
user.profile = MagicMock()

# CORRECT - Create a real instance
UserProfile.objects.create(
    user=user,
    supabase_uid='test-uid',  # Supply all required fields
    credits_balance=0
)
```

2. **Mock Methods, Not Relations**: If you need to mock behavior, use `patch` to mock specific methods rather than trying to replace entire model instances:

```python
# Mock a specific method
with patch('apps.users.models.UserProfile.add_credits') as mock_add_credits:
    mock_add_credits.return_value = None
    # Test code here
```

3. **Use Factory Libraries**: For complex models, consider using libraries like `factory_boy` to create test instances with less boilerplate code.

## Stripe API Client Patching Issues

### Problem: Incorrect Stripe Client Patching

When writing tests for Stripe integration, you may encounter errors like this when trying to patch the Stripe client incorrectly:

```
AttributeError: <module 'stripe' from '...'> does not have the attribute 'Stripe'
```

This happens because the Stripe Python library doesn't have a `Stripe` class, but instead uses `StripeClient` or the module-level functions directly.

### Solution:

1. **Patch the Correct Import or Function**: Instead of patching `stripe.Stripe`, patch the specific function or class that's actually used in your code:

```python
# WRONG - This will fail:
@patch('stripe.Stripe')
def test_something(self, mock_stripe):
    # Test code

# CORRECT - Patch the function that returns the client
@patch('apps.stripe_home.views.get_stripe_client')
def test_something(self, mock_get_stripe_client):
    # Create a mock client
    mock_stripe_client = MagicMock()
    mock_get_stripe_client.return_value = mock_stripe_client
    # Test code
```

2. **Check Your Actual Implementation**: Look at how your code instantiates the Stripe client. Common patterns include:
   - `StripeClient(api_key)` (stripe.StripeClient)
   - Module-level functions (stripe.Customer.create, etc.)
   - A wrapper function like `get_stripe_client()`

3. **Use Consistent Patching**: If the same client is used in multiple places, patch it at the source:

```python
# If using a utility function that creates the client
@patch('apps.stripe_home.config.get_stripe_client')
```

## True End-to-End Testing vs. Mocking

### Problem: Mixed Testing Strategy Issues

You might encounter confusing test failures when you're trying to do "true end-to-end testing" but still mocking some components. This can lead to assertions checking for mocked calls that never happen because the real code runs instead.

```python
# This will fail because the real function runs, not the mock
@patch('apps.stripe_home.credit.allocate_subscription_credits')
def test_allocation(self, mock_allocate):
    # Call real view code that also calls the real allocate function
    # The mock won't be called!
    mock_allocate.assert_called_once()  # This will fail
```

### Solution:

1. **Choose a consistent approach**: Either:
   - True end-to-end: Don't mock internal functions, instead check the actual results/state changes
   - Unit testing: Mock dependencies, but test only one layer at a time

2. **For true end-to-end tests**:
   - Only mock external APIs (Stripe, etc.)
   - Verify real state changes (database values, etc.)
   - Use assertions like:
   ```python
   # Check the actual result rather than if a mock was called
   self.assertEqual(user.profile.credits_balance, expected_amount)
   ```

3. **For mixed integration tests**:
   - Mock only at architectural boundaries
   - Be explicit about which components are real vs. mocked
   - Document your testing strategy

## Further Resources

- [Django App Configuration Documentation](https://docs.djangoproject.com/en/stable/ref/applications/)
- [Stripe API Test Documentation](https://stripe.com/docs/testing)
- [Django Testing Best Practices](https://docs.djangoproject.com/en/stable/topics/testing/)
