# Stripe Webhook Implementation Guide

## Overview

This document outlines the implementation of Stripe webhooks in our Django-Supabase template, focusing on handling subscription events, payment processing, and credit allocation.

Webhooks are particularly important for subscription-based services as they allow your application to be notified of asynchronous events such as subscription creations, updates, and cancellations.

## Table of Contents

1. [Webhook Setup](#webhook-setup)
2. [Event Types](#event-types)
3. [Webhook Handler Implementation](#webhook-handler-implementation)
4. [Testing Strategy](#testing-strategy)
5. [Security Considerations](#security-considerations)
6. [Production Deployment](#production-deployment)

## Webhook Setup

### 1. Configure Webhook Endpoint in Stripe Dashboard

1. Log in to the [Stripe Dashboard](https://dashboard.stripe.com/)
2. Navigate to Developers > Webhooks
3. Click "Add endpoint"
4. Enter your webhook URL: `https://your-domain.com/api/stripe/webhook/`
5. Select events to listen for (see [Event Types](#event-types) section)
6. Click "Add endpoint"
7. Copy the Webhook Signing Secret (starts with `whsec_`)
8. Add this secret to your `.env` file as `STRIPE_WEBHOOK_SECRET`

### 2. Configure Django URLs

```python
# urls.py
from django.urls import path
from apps.payments.views import StripeWebhookView

urlpatterns = [  
    path('api/stripe/webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
    # Other URLs
]
```

## Event Types

Implement handlers for these key Stripe webhook events:

| Event Type | Description | Action |
|------------|-------------|--------|
| `customer.subscription.created` | New subscription created | Create subscription record, update user tier, allocate initial credits |
| `customer.subscription.updated` | Subscription updated | Update subscription record, modify user tier if needed |
| `customer.subscription.deleted` | Subscription cancelled or ended | Mark subscription as cancelled, update user tier |
| `invoice.payment_succeeded` | Subscription payment successful | Record payment, allocate monthly credits |
| `invoice.payment_failed` | Subscription payment failed | Update subscription status, send notification |
| `checkout.session.completed` | Checkout completed | Process new subscription or one-time purchase |
| `customer.updated` | Customer details updated | Update local customer data |
| `payment_intent.succeeded` | Payment completed successfully | Record successful payment |
| `payment_intent.payment_failed` | Payment attempt failed | Record failed payment, handle retry logic |
| `charge.refunded` | Payment refunded | Process refund, adjust credits if needed |
| `charge.dispute.created` | Dispute/chargeback created | Flag account, record dispute details |
| `radar.early_fraud_warning.created` | Potential fraud detected | Flag account for review, record warning |

## Webhook Handler Implementation

### 1. Base Webhook Handler

```python
# apps/payments/views.py
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from stripe import StripeClient, Webhook
import logging

logger = logging.getLogger(__name__)

class StripeWebhookView(APIView):
    """Handle Stripe webhook events"""
    authentication_classes = []  # No authentication for webhooks
    permission_classes = []  # No permissions for webhooks
    
    def post(self, request):
        stripe_client = StripeClient(settings.STRIPE_SECRET_KEY)
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        
        if not sig_header:
            logger.error("No Stripe signature header found")
            return Response({'error': 'No signature header'}, status=400)
        
        try:
            event = Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            # Invalid payload
            logger.error(f"Invalid Webhook payload: {str(e)}")
            return Response({'error': str(e)}, status=400)
        except Exception as e:
            # Invalid signature
            logger.error(f"Invalid Webhook signature: {str(e)}")
            return Response({'error': str(e)}, status=400)
        
        # Log event receipt for debugging/auditing
        logger.info(f"Stripe webhook received: {event.type} - {event.id}")
        
        # Handle event based on type
        handled = self.handle_event(event, stripe_client)
        
        if handled:
            return Response({'status': 'success', 'event': event.type})
        else:
            logger.warning(f"Unhandled webhook event type: {event.type}")
            return Response({'status': 'ignored', 'event': event.type})
    
    def handle_event(self, event, stripe_client):
        """Route event to appropriate handler method"""
        handlers = {
            'customer.subscription.created': self._handle_subscription_created,
            'customer.subscription.updated': self._handle_subscription_updated,
            'customer.subscription.deleted': self._handle_subscription_deleted,
            'invoice.payment_succeeded': self._handle_invoice_payment_succeeded,
            'invoice.payment_failed': self._handle_invoice_payment_failed,
            'checkout.session.completed': self._handle_checkout_session_completed,
            'customer.updated': self._handle_customer_updated,
            'payment_intent.succeeded': self._handle_payment_intent_succeeded,
            'payment_intent.payment_failed': self._handle_payment_intent_failed,
            'charge.refunded': self._handle_charge_refunded,
            'charge.dispute.created': self._handle_dispute_created,
            'radar.early_fraud_warning.created': self._handle_fraud_warning_created,
        }
        
        handler = handlers.get(event.type)
        if handler:
            try:
                handler(event.data.object, stripe_client)
                return True
            except Exception as e:
                logger.error(f"Error handling {event.type}: {str(e)}")
                # Still return True as we've acknowledged receipt
                return True
        
        return False
```

### 2. Subscription Event Handlers

```python
def _handle_subscription_created(self, subscription, stripe_client):
    """Handle new subscription creation"""
    from django.contrib.auth import get_user_model
    from apps.payments.models import StripeCustomer, StripeSubscription, StripePlan
    from apps.credits.models import CreditTransaction
    from django.utils import timezone
    import json
    
    User = get_user_model()
    
    # Find the user associated with this subscription
    try:
        # Get customer ID from subscription
        customer_id = subscription.customer
        
        # Look up our customer record
        customer = StripeCustomer.objects.get(customer_id=customer_id)
        user = customer.user
        
        # Get subscription details
        plan_id = subscription.items.data[0].price.id
        
        # Find or create our local plan record
        try:
            plan = StripePlan.objects.get(plan_id=plan_id)
        except StripePlan.DoesNotExist:
            # Fetch plan details from Stripe
            stripe_price = stripe_client.prices.retrieve(plan_id)
            stripe_product = stripe_client.products.retrieve(stripe_price.product)
            
            # Create local plan record
            plan = StripePlan.objects.create(
                plan_id=plan_id,
                name=stripe_product.name,
                amount=stripe_price.unit_amount,
                currency=stripe_price.currency,
                interval=stripe_price.recurring.interval,
                # Set initial and monthly credits based on your business logic
                initial_credits=self._get_initial_credits(stripe_product),
                monthly_credits=self._get_monthly_credits(stripe_product),
                livemode=subscription.livemode
            )
        
        # Create subscription record
        new_subscription = StripeSubscription.objects.create(
            user=user,
            subscription_id=subscription.id,
            status=subscription.status,
            plan_id=plan_id,
            current_period_start=timezone.datetime.fromtimestamp(subscription.current_period_start),
            current_period_end=timezone.datetime.fromtimestamp(subscription.current_period_end),
            cancel_at_period_end=subscription.cancel_at_period_end,
            livemode=subscription.livemode
        )
        
        # Update user profile subscription tier
        profile = user.profile
        profile.subscription_tier = self._map_plan_to_tier(plan.name)
        profile.save(update_fields=['subscription_tier'])
        
        # Allocate initial credits if applicable
        if plan.initial_credits > 0 and subscription.status == 'active':
            old_balance = profile.credits_balance
            profile.add_credits(plan.initial_credits)
            
            # Record transaction
            CreditTransaction.objects.create(
                user=user,
                transaction_type='addition',
                amount=plan.initial_credits,
                balance_after=old_balance + plan.initial_credits,
                description=f'Initial subscription credits for {plan.name}',
                endpoint='stripe.subscription.created',
                reference_id=subscription.id
            )
        
        logger.info(f"Created subscription {subscription.id} for user {user.id}")
        return True
        
    except StripeCustomer.DoesNotExist:
        logger.error(f"No customer found for ID {subscription.customer}")
        return False
    except Exception as e:
        logger.error(f"Error processing subscription: {str(e)}")
        return False
```

## Testing Strategy

### 1. Setting Up Pytest for Stripe Testing

Install required packages:

```bash
pip install pytest pytest-django pytest-mock factory-boy
```

Add to `pytest.ini` at project root:

```ini
[pytest]
DJANGO_SETTINGS_MODULE=config.settings.test
python_files = test_*.py
testpaths = tests
```

### 2. Creating Stripe Webhook Test Fixtures

```python
# tests/fixtures/stripe_fixtures.py
import pytest
import json
import os
from stripe import Webhook
from django.conf import settings

@pytest.fixture
def stripe_webhook_secret():
    """Return test webhook secret"""
    return 'whsec_test_secret'

@pytest.fixture
def stripe_signature(stripe_webhook_secret):
    """Generate a valid Stripe signature for testing"""
    timestamp = int(time.time())
    payload = '{"object": {"id": "test_id"}}'  # Simple test payload
    signature = Webhook.generate_test_header(
        payload=payload,
        secret=stripe_webhook_secret,
        timestamp=timestamp
    )
    return signature

@pytest.fixture
def stripe_event_factory():
    """Factory for creating Stripe event objects"""
    def _factory(event_type, object_data=None):
        if not object_data:
            object_data = {}
        
        # Load event template from fixtures if available
        fixture_path = os.path.join(
            settings.BASE_DIR, 'tests', 'fixtures', 'stripe_events', f"{event_type}.json"
        )
        
        if os.path.exists(fixture_path):
            with open(fixture_path, 'r') as f:
                event_data = json.load(f)
                # Merge provided object data
                if object_data:
                    event_data['data']['object'].update(object_data)
        else:
            # Create minimal event structure
            event_data = {
                'id': f"evt_test_{event_type.replace('.', '_')}",
                'type': event_type,
                'data': {
                    'object': object_data
                }
            }
        
        return event_data
    
    return _factory
```

### 3. Sample Test for Webhook Handler

```python
# tests/apps/payments/test_webhooks.py
import pytest
import json
from django.urls import reverse
from rest_framework.test import APIClient
from stripe import Webhook
from django.utils import timezone
from apps.payments.views import StripeWebhookView
from apps.payments.models import StripeCustomer, StripeSubscription, StripePlan
from apps.credits.models import CreditTransaction

@pytest.mark.django_db
class TestStripeWebhooks:
    
    @pytest.fixture
    def api_client(self):
        return APIClient()
    
    @pytest.fixture
    def webhook_url(self):
        return reverse('stripe-webhook')
    
    @pytest.fixture
    def user(self, django_user_model):
        return django_user_model.objects.create(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
    
    @pytest.fixture
    def stripe_customer(self, user):
        return StripeCustomer.objects.create(
            user=user,
            customer_id='cus_test123',
            livemode=False
        )
    
    @pytest.fixture
    def stripe_plan(self):
        return StripePlan.objects.create(
            plan_id='price_test123',
            name='Test Plan',
            amount=1000,  # $10.00
            currency='usd',
            interval='month',
            initial_credits=100,
            monthly_credits=50,
            livemode=False
        )
    
    def test_subscription_created_event(self, monkeypatch, api_client, webhook_url, 
                                        stripe_webhook_secret, stripe_signature, 
                                        stripe_event_factory, stripe_customer, stripe_plan):
        """Test handling of subscription.created event"""
        # Create event data
        current_time = int(timezone.now().timestamp())
        event_data = stripe_event_factory('customer.subscription.created', {
            'id': 'sub_test123',
            'customer': stripe_customer.customer_id,
            'status': 'active',
            'current_period_start': current_time,
            'current_period_end': current_time + 30*24*60*60,  # 30 days
            'cancel_at_period_end': False,
            'items': {
                'data': [{
                    'price': {
                        'id': stripe_plan.plan_id
                    }
                }]
            },
            'livemode': False
        })
        
        # Mock settings and webhook verification
        monkeypatch.setattr('django.conf.settings.STRIPE_WEBHOOK_SECRET', stripe_webhook_secret)
        monkeypatch.setattr('stripe.Webhook.construct_event', 
                        lambda payload, sig, secret: event_data)
        
        # Send webhook request
        response = api_client.post(
            webhook_url,
            data=json.dumps(event_data),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE=stripe_signature
        )
        
        # Assert response
        assert response.status_code == 200
        assert response.data['status'] == 'success'
        
        # Assert subscription created
        subscription = StripeSubscription.objects.filter(subscription_id='sub_test123').first()
        assert subscription is not None
        assert subscription.status == 'active'
        assert subscription.plan_id == stripe_plan.plan_id
        
        # Assert credits allocated
        user = stripe_customer.user
        transaction = CreditTransaction.objects.filter(
            user=user,
            transaction_type='addition',
            amount=stripe_plan.initial_credits
        ).first()
        assert transaction is not None
        
        # Assert user profile updated
        user.profile.refresh_from_db()
        assert user.profile.credits_balance >= stripe_plan.initial_credits
```

### 4. Test for Fraud Warning Handlers

```python
@pytest.mark.django_db
def test_fraud_warning_event(self, monkeypatch, api_client, webhook_url, 
                           stripe_webhook_secret, stripe_signature, 
                           stripe_event_factory, stripe_customer):
    """Test handling of radar.early_fraud_warning.created event"""
    # Create event data
    event_data = stripe_event_factory('radar.early_fraud_warning.created', {
        'id': 'issfr_test123',
        'charge': 'ch_test123',
        'risk_level': 'high',
        'reason': 'card_never_verified',
        'livemode': False
    })
    
    # Mock settings, webhook verification, and charge retrieval
    monkeypatch.setattr('django.conf.settings.STRIPE_WEBHOOK_SECRET', stripe_webhook_secret)
    monkeypatch.setattr('stripe.Webhook.construct_event', 
                    lambda payload, sig, secret: event_data)
    
    # Mock the charge retrieval to return our customer's ID
    class MockCharge:
        customer = stripe_customer.customer_id
    
    monkeypatch.setattr('stripe.StripeClient.charges.retrieve', 
                    lambda self, charge_id: MockCharge())
    
    # Send webhook request
    response = api_client.post(
        webhook_url,
        data=json.dumps(event_data),
        content_type='application/json',
        HTTP_STRIPE_SIGNATURE=stripe_signature
    )
    
    # Assert response
    assert response.status_code == 200
    assert response.data['status'] == 'success'
    
    # Assert fraud warning created
    from apps.payments.models import StripeFraudWarning
    warning = StripeFraudWarning.objects.filter(warning_id='issfr_test123').first()
    assert warning is not None
    assert warning.user == stripe_customer.user
    assert warning.risk_level == 'high'
```

## Security Considerations

### 1. Always Verify Webhook Signatures

Stripe webhook signatures help ensure that webhook events are legitimate and were actually sent by Stripe. Always verify the signature using Stripe's provided libraries.

### 2. Use Environment Variables for API Keys

Store all Stripe keys and secrets in environment variables, never hardcode them in your application.

### 3. Handle PCI Compliance

Using Stripe Elements and Checkout keeps most PCI compliance burden on Stripe. However, make sure not to log or store any sensitive card data.

### 4. Idempotency

Webhook events may occasionally be sent more than once. Implement idempotency to ensure you don't process the same event multiple times.

## Production Deployment

### 1. Enable Webhooks in Production

Ensure you create separate webhook endpoints for production with appropriate signing secrets.

### 2. Monitor Webhook Failures

Set up monitoring for webhook failures. Stripe's dashboard provides webhook logs, but you should also log failures in your application.

### 3. Retry Mechanism

Implement a retry mechanism for failed webhook handling. This can be through Celery tasks or other background job processors.

### 4. Set Up Alerts

Configure alerts for critical webhook failures, especially those related to payment failures and fraud warnings.

### 5. Use Stripe CLI for Local Testing

The Stripe CLI allows you to forward webhook events to your local development environment:

```bash
# Install Stripe CLI from https://stripe.com/docs/stripe-cli
stripe login
stripe listen --forward-to http://localhost:8000/api/stripe/webhook/
