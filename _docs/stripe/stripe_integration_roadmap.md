# Stripe Integration Roadmap

## Overview

This document outlines the comprehensive plan for integrating Stripe into our Django-Supabase template, focusing on subscription management, credit allocation, and fraud reporting for our SaaS application.

## Table of Contents

1. [Core Stripe Features](#core-stripe-features)
2. [Subscription Management](#subscription-management)
3. [Payment Processing Options](#payment-processing-options)
4. [Credit Allocation System](#credit-allocation-system)
5. [Webhook Integration](#webhook-integration)
6. [Fraud Detection and Reporting](#fraud-detection-and-reporting)
7. [Testing Strategy](#testing-strategy)
8. [Implementation Timeline](#implementation-timeline)

## Core Stripe Features

### 1. Stripe Client Integration

```python
from stripe import StripeClient

def get_stripe_client():
    from django.conf import settings
    return StripeClient(settings.STRIPE_SECRET_KEY)
```

### 2. Stripe Test Mode

Implement comprehensive test mode support:

```python
class StripeConfig:
    @classmethod
    def is_test_mode(cls):
        from django.conf import settings
        return settings.STRIPE_SECRET_KEY.startswith('sk_test_')
    
    @classmethod
    def get_test_card_numbers(cls):
        """Return test card numbers for different scenarios"""
        return {
            'success': '4242424242424242',
            'requires_auth': '4000002500003155',
            'declined': '4000000000000002',
            'insufficient_funds': '4000000000009995',
            'processing_error': '4000000000000119',
        }
    
    @classmethod
    def get_test_dashboard_url(cls, object_id, object_type):
        """Generate Stripe dashboard URL for test objects"""
        base_url = 'https://dashboard.stripe.com/test/'
        paths = {
            'customer': f'customers/{object_id}',
            'subscription': f'subscriptions/{object_id}',
            'payment': f'payments/{object_id}',
            'invoice': f'invoices/{object_id}',
        }
        return base_url + paths.get(object_type, '')
```

### 3. Data Models

#### a. StripeCustomer Model

```python
class StripeCustomer(models.Model):
    """Link between Django user and Stripe customer"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    customer_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    livemode = models.BooleanField(default=False)
    
    def get_dashboard_url(self):
        """Get URL to view this customer in Stripe dashboard"""
        if self.livemode:
            return f"https://dashboard.stripe.com/customers/{self.customer_id}"
        return f"https://dashboard.stripe.com/test/customers/{self.customer_id}"
```

#### b. StripeSubscription Model

```python
class StripeSubscription(models.Model):
    """Store subscription information"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('unpaid', 'Unpaid'),
        ('canceled', 'Canceled'),
        ('incomplete', 'Incomplete'),
        ('incomplete_expired', 'Incomplete Expired'),
        ('trialing', 'Trialing'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='stripe_subscriptions')
    subscription_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    plan_id = models.CharField(max_length=255)
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    cancel_at_period_end = models.BooleanField(default=False)
    livemode = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

#### c. StripePlan Model

```python
class StripePlan(models.Model):
    """Store plan information from Stripe"""
    plan_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    amount = models.IntegerField()  # in cents
    currency = models.CharField(max_length=3, default='usd')
    interval = models.CharField(max_length=20)  # month, year, etc.
    initial_credits = models.IntegerField(default=0)  # Credits given upon subscription
    monthly_credits = models.IntegerField(default=0)  # Credits given monthly
    features = models.JSONField(default=dict)  # Store plan features as JSON
    active = models.BooleanField(default=True)
    livemode = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

## Subscription Management

### 1. Customer Portal Integration

Implement Stripe Customer Portal for self-service subscription management:

```python
class CustomerPortalView(APIView):
    """Create a Stripe Customer Portal session for self-service management"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        stripe_client = get_stripe_client()
        
        try:
            # Get customer
            customer = StripeCustomer.objects.get(user=request.user)
            
            # Create portal session
            session = stripe_client.billing_portal.sessions.create(
                customer=customer.customer_id,
                return_url=request.build_absolute_uri('/account/'),
            )
            
            return Response({'url': session.url})
        except StripeCustomer.DoesNotExist:
            return Response({'error': 'No Stripe customer found'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=400)
```

### 2. Subscription Creation via Checkout

```python
class CreateCheckoutSessionView(APIView):
    """Create a Stripe checkout session for subscription"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        stripe_client = get_stripe_client()
        
        # Get plan details
        plan_id = request.data.get('plan_id')
        plan = StripePlan.objects.get(id=plan_id)
        
        # Create or get Stripe customer
        customer, created = StripeCustomer.objects.get_or_create(
            user=request.user,
            defaults={
                'customer_id': create_stripe_customer(request.user),
                'livemode': not StripeConfig.is_test_mode()
            }
        )
        
        # Create checkout session
        checkout_session = stripe_client.checkout.sessions.create(
            customer=customer.customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': plan.plan_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.build_absolute_uri('/subscription/success?session_id={CHECKOUT_SESSION_ID}'),
            cancel_url=request.build_absolute_uri('/subscription/cancel'),
            allow_promotion_codes=True,
            billing_address_collection='required',
            client_reference_id=str(request.user.id),
        )
        
        return Response({'checkout_url': checkout_session.url})
    
    def create_stripe_customer(self, user):
        stripe_client = get_stripe_client()
        customer = stripe_client.customers.create(
            email=user.email,
            name=f"{user.first_name} {user.last_name}".strip() or user.username,
            metadata={
                'user_id': str(user.id),
                'username': user.username
            }
        )
        return customer.id
```

### 3. Direct Payment Links Integration

Implement Stripe Payment Links for direct subscription access:

```python
class PaymentLinkView(APIView):
    """Generate or retrieve persistent payment links for plans"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, plan_id=None):
        stripe_client = get_stripe_client()
        
        if plan_id:
            # Get specific plan payment link
            try:
                plan = StripePlan.objects.get(id=plan_id, active=True)
                payment_link = self._get_or_create_payment_link(plan)
                return Response({'payment_link': payment_link})
            except StripePlan.DoesNotExist:
                return Response({'error': 'Plan not found'}, status=404)
        else:
            # Get all active plan payment links
            plans = StripePlan.objects.filter(active=True)
            payment_links = {}
            
            for plan in plans:
                payment_links[plan.name] = self._get_or_create_payment_link(plan)
            
            return Response({'payment_links': payment_links})
    
    def _get_or_create_payment_link(self, plan):
        stripe_client = get_stripe_client()
        
        # Look for existing link in metadata
        if plan.metadata and plan.metadata.get('payment_link_id'):
            try:
                link = stripe_client.payment_links.retrieve(plan.metadata['payment_link_id'])
                return link.url
            except:
                # Link no longer exists, create new one
                pass
        
        # Create new payment link
        link = stripe_client.payment_links.create(
            line_items=[{
                'price': plan.plan_id,
                'quantity': 1,
            }],
            after_completion={
                'type': 'redirect',
                'redirect': {
                    'url': f"{settings.BASE_URL}/subscription/success",
                },
            },
            allow_promotion_codes=True,
            billing_address_collection='required',
            metadata={
                'plan_id': str(plan.id),
                'plan_name': plan.name,
            }
        )
        
        # Save link ID to plan metadata for future reference
        if not plan.metadata:
            plan.metadata = {}
        plan.metadata['payment_link_id'] = link.id
        plan.save(update_fields=['metadata'])
        
        return link.url
```

## Payment Processing Options

### 1. Checkout Sessions

```python
def create_checkout_session(user, plan, success_url, cancel_url):
    """Create a Stripe checkout session for immediate payment"""
    stripe_client = get_stripe_client()
    
    # Get or create customer
    customer, created = StripeCustomer.objects.get_or_create(
        user=user,
        defaults={
            'customer_id': create_stripe_customer(user),
            'livemode': not StripeConfig.is_test_mode()
        }
    )
    
    # Create checkout session
    session = stripe_client.checkout.sessions.create(
        customer=customer.customer_id,
        payment_method_types=['card'],
        line_items=[{
            'price': plan.plan_id,
            'quantity': 1,
        }],
        mode='subscription',
        success_url=success_url,
        cancel_url=cancel_url,
        allow_promotion_codes=True,
        billing_address_collection='required',
        client_reference_id=str(user.id),
    )
    
    return session
```

### 2. Direct Payment Links

Implement Stripe-hosted payment links for a no-code checkout experience:

```python
def create_subscription_payment_link(plan, custom_fields=None, automatic_tax=False):
    """Create a payment link for subscription signup with Stripe-hosted UI"""
    stripe_client = get_stripe_client()
    
    line_items = [{
        'price': plan.plan_id,
        'quantity': 1,
    }]
    
    link_data = {
        'line_items': line_items,
        'after_completion': {
            'type': 'redirect',
            'redirect': {
                'url': f"{settings.BASE_URL}/subscription/success",
            },
        },
        'allow_promotion_codes': True,
        'billing_address_collection': 'required',
        'metadata': {
            'plan_id': str(plan.id),
            'plan_name': plan.name,
        }
    }
    
    # Add custom fields if provided
    if custom_fields:
        link_data['custom_fields'] = custom_fields
        
    # Enable automatic tax calculation if requested
    if automatic_tax:
        link_data['automatic_tax'] = {'enabled': True}
    
    return stripe_client.payment_links.create(**link_data)
```

### 3. Payment Links with Branding Customization

```python
def create_branded_payment_link(plan, branding_options=None):
    """Create a payment link with custom branding"""
    stripe_client = get_stripe_client()
    
    link_data = {
        'line_items': [{
            'price': plan.plan_id,
            'quantity': 1,
        }],
        'after_completion': {
            'type': 'redirect',
            'redirect': {
                'url': f"{settings.BASE_URL}/subscription/success",
            },
        },
        'allow_promotion_codes': True,
        'billing_address_collection': 'required',
    }
    
    # Add branding options if provided
    if branding_options:
        link_data['branding'] = branding_options
    
    return stripe_client.payment_links.create(**link_data)
```

## Credit Allocation System

### 1. Credit Allocation for New Subscriptions

```python
def allocate_subscription_credits(user, plan, subscription_id):
    """Allocate initial credits when a new subscription is created"""
    from apps.credits.models import CreditTransaction
    
    profile = user.profile
    old_balance = profile.credits_balance
    
    # Add credits to user profile
    profile.add_credits(plan.initial_credits)
    
    # Record transaction
    CreditTransaction.objects.create(
        user=user,
        transaction_type='addition',
        amount=plan.initial_credits,
        balance_after=old_balance + plan.initial_credits,
        description=f'Initial subscription credits for {plan.name}',
        endpoint='stripe.subscription',
        reference_id=subscription_id
    )
```

### 2. Monthly Credit Allocation

```python
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

class Command(BaseCommand):
    help = 'Allocate monthly credits to active subscribers'
    
    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model
        from apps.users.models import UserProfile
        from apps.payments.models import StripeSubscription, StripePlan
        
        User = get_user_model()
        today = timezone.now().date()
        
        # Get active subscriptions
        active_subscriptions = StripeSubscription.objects.filter(
            status='active',
            current_period_end__gte=timezone.now()
        )
        
        processed_count = 0
        error_count = 0
        
        for subscription in active_subscriptions:
            user = subscription.user
            
            try:
                with transaction.atomic():
                    profile = UserProfile.objects.select_for_update().get(user=user)
                    
                    # Skip if credits already allocated this month
                    if (profile.last_credit_allocation_date and 
                        profile.last_credit_allocation_date.month == today.month and
                        profile.last_credit_allocation_date.year == today.year):
                        continue
                    
                    # Get plan and credit amount
                    plan = StripePlan.objects.get(plan_id=subscription.plan_id)
                    credit_amount = plan.monthly_credits
                    
                    if credit_amount > 0:
                        # Add credits
                        old_balance = profile.credits_balance
                        profile.add_credits(credit_amount)
                        
                        # Update allocation date
                        profile.last_credit_allocation_date = today
                        profile.save(update_fields=['last_credit_allocation_date'])
                        
                        # Record transaction
                        from apps.credits.models import CreditTransaction
                        CreditTransaction.objects.create(
                            user=user,
                            transaction_type='addition',
                            amount=credit_amount,
                            balance_after=old_balance + credit_amount,
                            description=f'Monthly subscription credits for {plan.name}',
                            endpoint='stripe.monthly_allocation',
                            reference_id=subscription.subscription_id
                        )
                        
                        processed_count += 1
            except Exception as e:
                self.stderr.write(f"Error processing user {user.id}: {str(e)}")
                error_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f"Monthly credits allocated: {processed_count} users processed, {error_count} errors"
        ))
```

## Webhook Integration

### 1. Stripe Webhook Handler

```python
class StripeWebhookView(APIView):
    """Handle Stripe webhook events"""
    # No authentication - uses Stripe's webhook signature
    authentication_classes = []
    permission_classes = []
    
    def post(self, request):
        stripe_client = get_stripe_client()
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            # Invalid payload
            return Response({'error': str(e)}, status=400)
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            return Response({'error': str(e)}, status=400)
        
        # Handle specific events
        event_handlers = {
            'customer.subscription.created': self._handle_subscription_created,
            'customer.subscription.updated': self._handle_subscription_updated,
            'customer.subscription.deleted': self._handle_subscription_deleted,
            'invoice.payment_succeeded': self._handle_invoice_payment_succeeded,
            'invoice.payment_failed': self._handle_invoice_payment_failed,
            'checkout.session.completed': self._handle_checkout_session_completed,
            'charge.succeeded': self._handle_charge_succeeded,
            'charge.refunded': self._handle_charge_refunded,
            'radar.early_fraud_warning.created': self._handle_fraud_warning
        }
        
        handler = event_handlers.get(event.type)
        if handler:
            try:
                handler(event.data.object)
            except Exception as e:
                # Log the error but return 200 to acknowledge receipt
                logger.error(f"Error handling {event.type}: {str(e)}")
        
        # Return success response to acknowledge receipt
        return Response({'status': 'success'})
```

### 2. Key Webhook Events to Handle

- `customer.subscription.created`: New subscription created
- `customer.subscription.updated`: Subscription updated (plan change, etc.)
- `customer.subscription.deleted`: Subscription cancelled or ended
- `invoice.payment_succeeded`: Payment successful, allocate credits
- `invoice.payment_failed`: Payment failed, update subscription status
- `checkout.session.completed`: Checkout completed successfully
- `charge.succeeded`: Payment charge succeeded
- `charge.refunded`: Payment refunded
- `radar.early_fraud_warning.created`: Potential fraud detected

## Fraud Detection and Reporting

### 1. Fraud Warning Model

```python
class StripeFraudWarning(models.Model):
    """Store fraud warnings from Stripe"""
    warning_id = models.CharField(max_length=255, unique=True)
    charge_id = models.CharField(max_length=255, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    risk_level = models.CharField(max_length=50)
    reason = models.CharField(max_length=255)
    status = models.CharField(max_length=50, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    livemode = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Stripe Fraud Warning'
        verbose_name_plural = 'Stripe Fraud Warnings'
        ordering = ['-created_at']
```

### 2. Fraud Warning Handler

```python
def _handle_fraud_warning(self, warning):
    """Handle fraud warnings from Stripe"""
    stripe_client = get_stripe_client()
    from django.contrib.auth import get_user_model
    from apps.payments.models import StripeCustomer, StripeFraudWarning
    
    User = get_user_model()
    
    # Find associated user
    user = None
    if warning.get('charge'):
        charge = stripe_client.charges.retrieve(warning.get('charge'))
        if charge.customer:
            try:
                stripe_customer = StripeCustomer.objects.get(customer_id=charge.customer)
                user = stripe_customer.user
            except StripeCustomer.DoesNotExist:
                pass
    
    # Create fraud warning record
    fraud_warning = StripeFraudWarning.objects.create(
        warning_id=warning.id,
        charge_id=warning.get('charge'),
        user=user,
        risk_level=warning.get('risk_level', 'unknown'),
        reason=warning.get('reason', 'unknown'),
        status=warning.get('status', 'open'),
        livemode=warning.get('livemode', False)
    )
    
    # Alert administrators
    self._send_fraud_alert(warning, user)
    
    # Take automatic action for high-risk fraud warnings
    if warning.get('risk_level') == 'highest' and user:
        # Flag user account
        profile = user.profile
        if not hasattr(profile, 'metadata') or profile.metadata is None:
            profile.metadata = {}
        profile.metadata['fraud_warning'] = True
        profile.metadata['fraud_warning_id'] = warning.id
        profile.metadata['fraud_warning_date'] = timezone.now().isoformat()
        profile.save(update_fields=['metadata'])
```

## Testing Strategy

### 1. Test Mode Configuration

```python
class TestStripeConfig:
    @staticmethod
    def get_test_cards():
        """Get test card numbers for different testing scenarios"""
        return {
            'success': '4242424242424242',
            'requires_auth': '4000002500003155',
            'declined': '4000000000000002',
            'insufficient_funds': '4000000000009995',
            'processing_error': '4000000000000119',
            'fraudulent': '4100000000000019',
        }
    
    @staticmethod
    def get_test_bank_accounts():
        """Get test bank account numbers"""
        return {
            'success': '000123456789',
            'insufficient_funds': '000222222222',
        }
    
    @staticmethod
    def get_test_webhook_payload(event_type):
        """Get test webhook payload for the specified event type"""
        # Implementation to generate test payloads for different event types
        pass
```

### 2. Test Classes for Stripe Integration

```python
from django.test import TestCase, override_settings
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from apps.users.models import UserProfile
from apps.credits.models import CreditTransaction
from apps.payments.models import (
    StripeCustomer, StripeSubscription, StripePlan, StripeFraudWarning
)

class StripeWebhookTestCase(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            supabase_uid='test-supabase-uid',
            credits_balance=0
        )
        self.plan = StripePlan.objects.create(
            plan_id='price_123',
            name='Basic Plan',
            amount=1000,  # $10.00
            interval='month',
            initial_credits=100,
            monthly_credits=50
        )
        self.stripe_customer = StripeCustomer.objects.create(
            user=self.user,
            customer_id='cus_123'
        )
    
    @patch('stripe.Webhook.construct_event')
    def test_subscription_created_webhook(self, mock_construct_event):
        # Mock event
        mock_event = MagicMock()
        mock_event.type = 'customer.subscription.created'
        mock_event.data.object = {
            'id': 'sub_123',
            'customer': 'cus_123',
            'status': 'active',
            'current_period_start': 1672531200,  # Jan 1, 2023
            'current_period_end': 1675209600,  # Feb 1, 2023
            'items': {
                'data': [{
                    'plan': {
                        'id': 'price_123'
                    }
                }]
            }
        }
        mock_construct_event.return_value = mock_event
        
        # Test webhook
        response = self.client.post(
            '/stripe/webhook/',
            HTTP_STRIPE_SIGNATURE='test_signature',
            content_type='application/json'
        )
        
        # Assert response
        self.assertEqual(response.status_code, 200)
        
        # Assert subscription created
        self.assertTrue(StripeSubscription.objects.filter(subscription_id='sub_123').exists())
        
        # Assert credits allocated
        transaction = CreditTransaction.objects.filter(
            user=self.user,
            transaction_type='addition',
            amount=100  # initial_credits from plan
        ).first()
        self.assertIsNotNone(transaction)
        
        # Assert profile updated
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.credits_balance, 100)
```

## Implementation Timeline

### Phase 1: Core Setup & Models (Week 1)

- Install Stripe library
- Configure test mode API keys
- Create data models
- Implement test infrastructure

### Phase 2: Subscription Management (Week 2)

- Implement subscription views
- Set up Checkout Sessions
- Create and configure Stripe Payment Links
- Implement Customer Portal for subscription management
- Configure automatic email receipts and notifications

### Phase 3: Credit Allocation System (Week 3)

- Implement initial credit allocation
- Set up monthly credit allocation
- Add credit transaction recording
- Test credit allocation flows

### Phase 4: Webhook Integration (Week 4)

- Implement webhook handlers for all events
- Set up event processing and error handling
- Add retry logic for failed operations
- Test with Stripe events

### Phase 5: Fraud Detection and Reporting (Week 5)

- Create fraud warning models
- Implement fraud handling
- Set up admin dashboard
- Add notification system for fraud alerts

### Phase 6: Testing and Production (Week 6)

- Comprehensive testing of the entire flow
- Documentation updates
- Production deployment
- Monitoring setup
