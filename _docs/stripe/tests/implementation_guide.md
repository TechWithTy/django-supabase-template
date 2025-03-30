# Stripe Integration Testing Implementation Guide

## Overview

This guide explains how to implement effective tests for the Stripe integration in our Django-Supabase application. It covers test strategies, tools, and best practices for ensuring that your Stripe integration remains reliable and bug-free.

## Setting Up the Test Environment

### Test Configuration

Our project uses pytest for running tests. The test configuration is set up to use SQLite as the test database for speed and simplicity.

```python
# Test database configuration in test_settings.py
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
```

### Stripe Test Keys

Always use Stripe's test API keys in your testing environment:

```python
# Settings for tests
STRIPE_SECRET_KEY = "sk_test_your_test_key"
STRIPE_PUBLISHABLE_KEY = "pk_test_your_test_key"
STRIPE_WEBHOOK_SECRET = "whsec_your_test_webhook_secret"
```

## Model Testing

### Basic Model Tests

Test the basic creation and validation of Stripe models:

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.stripe_home.models import StripeCustomer, StripePlan, StripeSubscription

User = get_user_model()

class StripeModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword"
        )
        
        self.plan = StripePlan.objects.create(
            plan_id="price_test123",
            name="Test Plan",
            amount=1999,
            interval="month",
            currency="usd",
            active=True
        )
        
        self.customer = StripeCustomer.objects.create(
            user=self.user,
            customer_id="cus_test123"
        )
    
    def test_stripe_customer_model(self):
        customer = StripeCustomer.objects.get(user=self.user)
        self.assertEqual(customer.customer_id, "cus_test123")
        self.assertEqual(str(customer), f"Customer: {self.user.email}")
        
    def test_stripe_plan_model(self):
        plan = StripePlan.objects.get(plan_id="price_test123")
        self.assertEqual(plan.amount, 1999)
        self.assertEqual(str(plan), "Test Plan")
        
    def test_stripe_subscription_model(self):
        subscription = StripeSubscription.objects.create(
            customer=self.customer,
            subscription_id="sub_test123",
            status="active",
            plan=self.plan,
            current_period_end="2025-12-31"
        )
        self.assertEqual(subscription.status, "active")
        self.assertEqual(str(subscription), f"Subscription: {self.user.email} - {self.plan.name}")
```

## View Testing

### Checkout Session Tests

Test the creation of checkout sessions:

```python
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.stripe_home.models import StripePlan

User = get_user_model()

class CheckoutSessionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword"
        )
        self.client.force_authenticate(user=self.user)
        
        self.plan = StripePlan.objects.create(
            plan_id="price_test123",
            name="Test Plan",
            amount=1999,
            interval="month",
            currency="usd",
            active=True
        )
    
    def test_create_checkout_session(self):
        # Use Stripe's test mode and mock the response if needed
        url = reverse("stripe:create-checkout-session")
        response = self.client.post(url, {"price_id": self.plan.plan_id})
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("session_id", response.data)
        self.assertIn("url", response.data)
```

### Webhook Tests

Test webhook event handling:

```python
import json
import stripe
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.stripe_home.models import StripeCustomer, StripePlan, StripeSubscription

User = get_user_model()

class WebhookTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword"
        )
        
        self.plan = StripePlan.objects.create(
            plan_id="price_test123",
            name="Test Plan",
            amount=1999,
            interval="month",
            currency="usd",
            active=True
        )
        
        self.customer = StripeCustomer.objects.create(
            user=self.user,
            customer_id="cus_test123"
        )
    
    def test_subscription_created_webhook(self):
        # Create a test event payload
        event_data = {
            "id": "evt_test123",
            "object": "event",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "object": "subscription",
                    "customer": "cus_test123",
                    "status": "active",
                    "items": {
                        "data": [{
                            "price": {
                                "id": "price_test123"
                            }
                        }]
                    },
                    "current_period_end": 1735689600  # 2025-01-01
                }
            }
        }
        
        # For real tests, you'd construct a properly signed webhook
        # For unit tests, we can mock Stripe's webhook verification
        url = reverse("stripe:webhook")
        response = self.client.post(
            url,
            data=json.dumps(event_data),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_signature"
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check that a subscription was created
        self.assertTrue(StripeSubscription.objects.filter(subscription_id="sub_test123").exists())
```

## Testing Product Management

Test the product management view for creating and updating Stripe products:

```python
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.stripe_home.models import StripePlan

User = get_user_model()

class ProductManagementTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="adminpassword",
            is_staff=True,
            is_superuser=True
        )
        self.client.force_authenticate(user=self.admin_user)
    
    def test_create_product_and_price(self):
        url = reverse("stripe:product-management")
        product_data = {
            "name": "Test Product",
            "description": "A test product",
            "prices": [
                {
                    "unit_amount": 1999,
                    "currency": "usd",
                    "interval": "month",
                    "initial_credits": 200,
                    "monthly_credits": 100
                }
            ]
        }
        
        response = self.client.post(url, product_data, format="json")
        
        self.assertEqual(response.status_code, 201)
        self.assertIn("product_id", response.data)
        self.assertIn("prices", response.data)
        
        # Check that the plan was created in the database
        price_id = response.data["prices"][0]["price_id"]
        self.assertTrue(StripePlan.objects.filter(plan_id=price_id).exists())
        
        plan = StripePlan.objects.get(plan_id=price_id)
        self.assertEqual(plan.amount, 1999)
        self.assertEqual(plan.interval, "month")
        self.assertEqual(plan.initial_credits, 200)
        self.assertEqual(plan.monthly_credits, 100)
```

## Working with Third-Party Mocks

For unit testing without calling the actual Stripe API, you can use libraries like `stripe-python-mock` or implement your own mocking:

```python
import unittest.mock as mock

# Mock Stripe API responses
@mock.patch("stripe.Customer.create")
@mock.patch("stripe.Subscription.create")
def test_create_subscription(self, mock_subscription_create, mock_customer_create):
    # Set up mock return values
    mock_customer_create.return_value = {
        "id": "cus_test123",
        "email": "test@example.com"
    }
    
    mock_subscription_create.return_value = {
        "id": "sub_test123",
        "status": "active",
        "current_period_end": 1735689600,  # 2025-01-01
        "items": {
            "data": [{
                "price": {
                    "id": "price_test123"
                }
            }]
        }
    }
    
    # Test your code that calls Stripe API
    # ...
```

## Test Coverage

Ensure thorough test coverage of your Stripe integration:

```bash
python -m pytest backend/apps/stripe_home/ --cov=backend.apps.stripe_home --cov-report=term-missing
```

Aim for at least 80% test coverage for core functionality.

## Continuous Integration

Include Stripe tests in your CI pipeline, but ensure that you're using test keys and mocking external API calls where appropriate.

```yaml
# Example GitHub Actions workflow excerpt
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      # ... setup steps
      - name: Run Stripe Tests
        run: python -m pytest backend/apps/stripe_home/
        env:
          STRIPE_SECRET_KEY: ${{ secrets.STRIPE_TEST_SECRET_KEY }}
          STRIPE_PUBLISHABLE_KEY: ${{ secrets.STRIPE_TEST_PUBLISHABLE_KEY }}
          STRIPE_WEBHOOK_SECRET: ${{ secrets.STRIPE_TEST_WEBHOOK_SECRET }}
```

## Related Resources

- [Troubleshooting Guide](./troubleshooting_guide.md): Common issues and solutions for Stripe tests
- [Stripe Testing Documentation](https://stripe.com/docs/testing)
- [Django Testing Best Practices](https://docs.djangoproject.com/en/stable/topics/testing/)
