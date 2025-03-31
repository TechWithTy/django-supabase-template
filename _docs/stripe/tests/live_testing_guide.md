# Stripe Integration Live Testing Guide

## Overview

This guide explains how to perform live testing with the Stripe API in our Django-Supabase application. Unlike mocked tests, these tests interact with the actual Stripe API using test keys and simulate the complete subscription and payment lifecycle.

## Test Setup Requirements

### 1. Environment Variables

You must configure the following environment variables in your `.env` file:

```
STRIPE_SECRET_KEY_TEST=sk_test_your_key_here
STRIPE_WEBHOOK_SECRET_TEST=whsec_your_webhook_secret_here
STRIPE_PUBLISHABLE_KEY_TEST=pk_test_your_key_here
```

### 2. Stripe Test Mode

These tests run against Stripe's test environment. Ensure your Stripe account is properly configured with test data and test webhooks. The tests will be skipped if a valid test key (starting with 'sk_test_') is not available.

### 3. Raw Card Data Restrictions

Stripe restricts sending raw card numbers to their API. Our tests use two approaches:

- Creating tokens from predefined test cards (e.g., 'tok_visa')
- Using Stripe's built-in test payment method tokens

Example using a test token:

```python
payment_method = stripe.PaymentMethod.create(
    type="card",
    card={
        "token": "tok_visa",  # Stripe's test token for Visa
    },
)
```

### 4. Test Resource Cleanup

Every test cleans up after itself by:

- Canceling created subscriptions
- Archiving products and prices
- Detaching payment methods
- Deleting customers

## Running the Tests

To run all Stripe integration tests:

```bash
python -m pytest backend/apps/stripe_home/tests/test_credit_integration.py -v
```

To run a specific test:

```bash
python -m pytest backend/apps/stripe_home/tests/test_credit_integration.py::StripeCreditIntegrationTest::test_initial_credit_allocation -v
```

To run with detailed logging (useful for debugging):

```bash
python -m pytest backend/apps/stripe_home/tests/test_credit_integration.py -v --log-cli-level=INFO
```

## Troubleshooting

### API Key Issues

If tests are being skipped, check that `STRIPE_SECRET_KEY_TEST` is correctly set in your `.env` file and that it starts with `sk_test_`.

### Card Errors

If you see card errors, try using Stripe's predefined test tokens:
- `tok_visa` - Visa card that succeeds
- `tok_visa_debit` - Debit card that succeeds
- `tok_mastercard` - Mastercard that succeeds
- `tok_visa_chargeDeclined` - Card that will be declined

### Webhook Errors

Ensure your webhook secret is correctly set up. You can generate a new webhook secret from the Stripe dashboard.

### Resource Cleanup

If tests leave resources behind, you may need to manually clean them up in the Stripe dashboard. Common resources to check:

- Customers
- Products
- Prices
- Subscriptions
- Payment methods

## Test Data

These tests create:

- Test users in the local database
- Stripe customers, products, prices, and subscriptions in Stripe's test environment
- Payment methods using Stripe's test tokens

## Debugging Webhook Handlers

When testing webhook functionality, our tests directly call the handler methods to simulate webhook events. If you're experiencing issues with webhook handlers, we recommend:

1. Using direct utility function calls in tests instead of webhook handlers
2. Using the Stripe CLI to forward webhooks to your local environment during development
3. Adding detailed logging to webhook handlers

## Common Test Scenarios

1. **Initial Credit Allocation**: Tests that users get correct initial credits when subscribing
2. **Monthly Credit Allocation**: Tests that recurring credits are added on successful payment
3. **Subscription Cancellation**: Tests proper cleanup of resources when subscriptions end
