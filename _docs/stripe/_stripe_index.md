# Stripe Integration Documentation

## Overview

This directory contains comprehensive documentation for integrating Stripe into the Django-Supabase template, focusing on subscription management, credit allocation, and fraud reporting for SaaS applications.

## Table of Contents

1. [Integration Roadmap](./stripe_integration_roadmap.md)
2. [Webhook Implementation](./stripe_webhook_implementation.md)
3. [Credit System Integration](./stripe_credit_system_integration.md)
4. [Stripe Checkout Sessions](#stripe-checkout-sessions)

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

## Stripe Checkout Sessions

### What is Stripe Checkout?

Stripe Checkout is a prebuilt, Stripe-hosted payment page that offers a complete payment experience without custom payment form development. Key benefits include:

- **Programmable UI** - Customize the flow while letting Stripe handle the complex parts
- **Optimized for conversion** - Includes smart features like address autocomplete 
- **Support for 25+ payment methods** - Credit cards, Apple Pay, Google Pay, and more
- **Automatic fraud prevention** - Radar protection built in
- **30+ language localizations** - Automatic language detection
- **Mobile optimized** - Works across all devices
- **Built-in support for SCA/3D Secure** - Compliant with EU regulations

### Creating Checkout Sessions for Subscriptions

```python
from django.conf import settings
from stripe import StripeClient
from apps.payments.models import StripePlan

def generate_subscription_checkout(plan_id, user):
    """Generate a Stripe Checkout Session for a subscription plan"""
    stripe_client = get_stripe_client()
    
    # Get plan details from database
    plan = StripePlan.objects.get(id=plan_id)
    
    # Create checkout session
    checkout_session = stripe_client.checkout.sessions.create(
        line_items=[{
            'price': plan.plan_id,  # Stripe price ID
            'quantity': 1,
        }],
        mode='subscription',
        success_url=f"{settings.BASE_URL}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.BASE_URL}/subscription/cancel",
        allow_promotion_codes=True,
        billing_address_collection='required',
        automatic_tax={'enabled': True},
        customer_email=user.email,  # Pre-populate customer email
        client_reference_id=str(user.id),  # Used to identify the user
        metadata={
            'plan_id': str(plan.id),
            'plan_name': plan.name,
            'user_id': str(user.id),
        }
    )
    
    return checkout_session.url
```

### Implementing the Checkout Sessions API View

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.payments.models import StripePlan

class CheckoutSessionView(APIView):
    """Generate Stripe Checkout Sessions for subscription plans"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, plan_id=None):
        """Create checkout session for a specific plan"""
        if not plan_id:
            return Response({'error': 'Plan ID required'}, status=400)
        
        try:
            plan = StripePlan.objects.get(id=plan_id, active=True)
            checkout_url = self._create_checkout_session(plan, request.user)
            return Response({
                'checkout_url': checkout_url
            })
        except StripePlan.DoesNotExist:
            return Response({'error': 'Plan not found'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=400)
    
    def _create_checkout_session(self, plan, user):
        """Create a Stripe Checkout Session"""
        stripe_client = get_stripe_client()
        
        # Create checkout session
        checkout_session = stripe_client.checkout.sessions.create(
            line_items=[{
                'price': plan.plan_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f"{settings.BASE_URL}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.BASE_URL}/subscription/cancel",
            allow_promotion_codes=True,
            billing_address_collection='required',
            customer_email=user.email,
            client_reference_id=str(user.id),
            metadata={
                'plan_id': str(plan.id),
                'plan_name': plan.name,
                'user_id': str(user.id),
            }
        )
        
        return checkout_session.url
```

### URL Configuration

```python
from django.urls import path
from apps.payments.views import CheckoutSessionView

urlpatterns = [
    path('subscription/checkout/<int:plan_id>/', CheckoutSessionView.as_view(), name='subscription_checkout'),
]
```

### Integrating Checkout in Your Frontend

```javascript
// Example JavaScript to redirect to Stripe Checkout
async function redirectToCheckout(planId) {
    try {
        const response = await fetch(`/api/subscription/checkout/${planId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),  // Include CSRF token
            },
        });
        
        const data = await response.json();
        if (data.checkout_url) {
            // Redirect to Stripe Checkout
            window.location.href = data.checkout_url;
        } else {
            console.error('Error creating checkout session:', data.error);
        }
    } catch (error) {
        console.error('Error:', error);
    }
}
```

### Handling Checkout Completion

When a customer completes their checkout, Stripe will redirect them to your success URL and trigger a `checkout.session.completed` webhook event. You'll need to handle this event to provision the customer's subscription and allocate credits.

```python
# In your webhook handler
def _handle_checkout_session_completed(self, session, stripe_client):
    """Handle checkout.session.completed webhook event"""
    from django.contrib.auth import get_user_model
    from apps.payments.models import StripeCustomer, StripeSubscription
    
    User = get_user_model()
    
    # Get user from client_reference_id
    if session.get('client_reference_id'):
        try:
            user_id = session.client_reference_id
            user = User.objects.get(id=user_id)
            
            # Create or get customer
            if session.customer:
                customer, created = StripeCustomer.objects.get_or_create(
                    user=user,
                    defaults={
                        'customer_id': session.customer,
                        'livemode': session.livemode,
                    }
                )
                if not created and customer.customer_id != session.customer:
                    customer.customer_id = session.customer
                    customer.save()
            
            # Handle subscription
            if session.mode == 'subscription' and session.subscription:
                # The subscription details will be processed by the 
                # customer.subscription.created webhook event
                logger.info(f"Checkout completed for user {user.id}, subscription: {session.subscription}")
            
            # For one-time purchases or credits top-up
            if session.mode == 'payment':
                # Process payment logic here
                logger.info(f"One-time payment completed for user {user.id}")
                
        except User.DoesNotExist:
            logger.error(f"User not found: {session.client_reference_id}")
        except Exception as e:
            logger.error(f"Error processing checkout session: {str(e)}")
```

### Alternative: Stripe Payment Links

If you need an even simpler solution without any server-side code for checkout, Stripe also offers Payment Links — shareable links that don't require any programming:

- No code required to create or share
- Can be created directly from the Stripe Dashboard
- Less customizable than Checkout Sessions
- Good for simple one-off payments

For subscription management, Checkout Sessions provide more flexibility and integration options.

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
