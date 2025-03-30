# Stripe Integration Test Troubleshooting Guide

## Common Testing Issues and Solutions

This document outlines common issues encountered when testing the Stripe integration and provides solutions to resolve them.

## Table of Contents
1. [App Registration Issues](#app-registration-issues)
2. [Database Table Naming](#database-table-naming)
3. [Import Path Problems](#import-path-problems)
4. [Migration Issues](#migration-issues)
5. [Testing Strategy](#testing-strategy)

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
```

## Further Resources

- [Django App Configuration Documentation](https://docs.djangoproject.com/en/stable/ref/applications/)
- [Stripe API Test Documentation](https://stripe.com/docs/testing)
- [Django Testing Best Practices](https://docs.djangoproject.com/en/stable/topics/testing/)
