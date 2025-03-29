# Stripe Integration Documentation

## Overview

This directory contains comprehensive documentation for integrating Stripe into the Django-Supabase template, focusing on Payment Links as the primary implementation method for subscription management, credit allocation, and fraud reporting for SaaS applications.

## Table of Contents

1. [Integration Roadmap](./stripe_integration_roadmap.md)
2. [Webhook Implementation](./stripe_webhook_implementation.md)
3. [Credit System Integration](./stripe_credit_system_integration.md)
4. [Payment Links Implementation](#payment-links-implementation)

## Implementation Guide

### Installation

First, install the official Stripe Python library:

```bash
pip install --upgrade stripe
```

### Configuration

Add the following to your `.env` file:

```
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

Update your `settings.py` to include these settings:

```python
# Stripe settings
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
```

### Client Initialization

Use the modern `StripeClient` approach recommended by Stripe:

```python
from stripe import StripeClient

def get_stripe_client():
    """Get a configured Stripe client instance"""
    from django.conf import settings
    return StripeClient(settings.STRIPE_SECRET_KEY)
```

## Payment Links Implementation

### What are Stripe Payment Links?

Payment Links are a Stripe feature that let you create a hosted payment page without any custom code or frontend development. Key benefits include:

- No frontend UI development required
- Customizable branding and appearance
- Support for 20+ payment methods (credit cards, Apple Pay, Google Pay, etc.)
- Automatic localization in 30+ languages
- Built-in discount code support
- Tax calculation support
- Automatic email receipts

### Creating Payment Links for Subscriptions

```python
from django.conf import settings
from stripe import StripeClient
from apps.payments.models import StripePlan

def generate_subscription_payment_link(plan_id):
    """Generate a payment link for a subscription plan"""
    stripe_client = get_stripe_client()
    
    # Get plan details from database
    plan = StripePlan.objects.get(id=plan_id)
    
    # Create payment link
    payment_link = stripe_client.payment_links.create(
        line_items=[{
            'price': plan.plan_id,  # Stripe price ID
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
        automatic_tax={'enabled': True},
        custom_fields=[
            {
                'key': 'user_email',
                'label': {'type': 'custom', 'custom': 'Email'},
                'type': 'text',
                'optional': False,
            },
        ],
        metadata={
            'plan_id': str(plan.id),
            'plan_name': plan.name,
        }
    )
    
    return payment_link.url
```

### Implementing the Payment Links API View

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.payments.models import StripePlan

class PaymentLinksView(APIView):
    """Generate payment links for subscription plans"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, plan_id=None):
        """Get payment link for specific plan or all active plans"""
        
        if plan_id:
            # Get link for specific plan
            try:
                plan = StripePlan.objects.get(id=plan_id, active=True)
                payment_link = self._get_or_create_payment_link(plan)
                return Response({
                    'plan_name': plan.name,
                    'payment_link': payment_link
                })
            except StripePlan.DoesNotExist:
                return Response({'error': 'Plan not found'}, status=404)
        else:
            # Get links for all active plans
            plans = StripePlan.objects.filter(active=True)
            links = {}
            
            for plan in plans:
                links[plan.name] = {
                    'id': plan.id,
                    'price': plan.amount / 100,  # Convert cents to dollars
                    'currency': plan.currency,
                    'interval': plan.interval,
                    'payment_link': self._get_or_create_payment_link(plan)
                }
            
            return Response({'plans': links})
    
    def _get_or_create_payment_link(self, plan):
        """Get existing payment link or create a new one"""
        stripe_client = get_stripe_client()
        
        # Check if plan has existing payment link in metadata
        if hasattr(plan, 'metadata') and plan.metadata and plan.metadata.get('payment_link_id'):
            try:
                link = stripe_client.payment_links.retrieve(plan.metadata['payment_link_id'])
                return link.url
            except Exception:
                # Link might be deleted or invalid, create new one
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
        if not hasattr(plan, 'metadata') or not plan.metadata:
            plan.metadata = {}
        plan.metadata['payment_link_id'] = link.id
        plan.save(update_fields=['metadata'])
        
        return link.url
```

### URL Configuration

```python
from django.urls import path
from apps.payments.views import PaymentLinksView

urlpatterns = [
    path('subscription/payment-links/', PaymentLinksView.as_view(), name='payment_links'),
    path('subscription/payment-links/<int:plan_id>/', PaymentLinksView.as_view(), name='plan_payment_link'),
]
```

### Displaying Payment Links in Your UI

Since the payment process happens on Stripe-hosted pages, your frontend only needs to provide links to the Stripe checkout:

```html
<!-- Example usage in a template -->
<div class="subscription-plans">
    {% for plan in plans %}
    <div class="plan-card">
        <h3>{{ plan.name }}</h3>
        <p class="price">${{ plan.amount|floatformat:2 }}/{{ plan.interval }}</p>
        <ul class="features">
            {% for feature in plan.features %}
            <li>{{ feature }}</li>
            {% endfor %}
        </ul>
        <a href="{{ plan.payment_link }}" class="subscribe-button">Subscribe Now</a>
    </div>
    {% endfor %}
</div>
```

## Documentation Files

### [Integration Roadmap](./stripe_integration_roadmap.md)

Comprehensive plan for integrating Stripe into the application, including:

- Setup and configuration
- Data models
- API endpoints
- Credit allocation system
- Subscription management
- Fraud detection
- Implementation timeline

### [Webhook Implementation](./stripe_webhook_implementation.md)

Detailed implementation guidance for Stripe webhooks:

- Configuration in Stripe Dashboard
- Event handling in Django
- Processing subscription events
- Credit allocation on successful payments
- Fraud warning processing
- Testing and deployment considerations

### [Credit System Integration](./stripe_credit_system_integration.md)

Details on integrating Stripe with the existing credit system:

- Credit allocation for new subscriptions
- Monthly credit allocation processes
- Credit transaction recording
- Subscription tier mapping
- Handling subscription changes and cancellations
