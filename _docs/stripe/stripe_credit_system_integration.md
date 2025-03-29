# Stripe Credit System Integration

## Overview

This document details how to integrate the existing credit-based system in our Django-Supabase template with Stripe subscriptions. The integration enables automatic credit allocation upon subscription creation and renewal, tiered credit allocation based on subscription plans, and proper handling of subscription changes.

## Table of Contents

1. [Credit System Integration](#credit-system-integration)
2. [Subscription Tiers and Credit Allocation](#subscription-tiers-and-credit-allocation)
3. [Credit Transaction Recording](#credit-transaction-recording)
4. [Monthly Credit Allocation](#monthly-credit-allocation)
5. [Credit Balance Management](#credit-balance-management)
6. [Implementation Examples](#implementation-examples)

## Credit System Integration

### 1. Connecting StripeSubscription to Credits

The integration between Stripe subscriptions and our credit system involves:

1. **Initial Credit Allocation**: When a user subscribes to a plan, they receive a set number of initial credits
2. **Recurring Credit Allocation**: On subscription renewal (monthly/yearly), users receive additional credits
3. **Subscription Tier Mapping**: Each Stripe plan maps to a subscription tier with different credit benefits
4. **Transaction Recording**: All credit changes are recorded in the `CreditTransaction` model

### 2. StripePlan Model Enhancement

The `StripePlan` model is key to defining credit allocation rules:

```python
class StripePlan(models.Model):
    """Store plan information from Stripe with credit allocation details"""
    plan_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    amount = models.IntegerField()  # in cents
    currency = models.CharField(max_length=3, default='usd')
    interval = models.CharField(max_length=20)  # month, year, etc.
    
    # Credit allocation settings
    initial_credits = models.IntegerField(
        default=0,
        help_text="Credits given upon subscription creation"
    )
    monthly_credits = models.IntegerField(
        default=0,
        help_text="Credits given on monthly renewal"
    )
    
    # Usage limits
    max_monthly_api_calls = models.IntegerField(
        default=1000,
        help_text="Maximum API calls allowed per month"
    )
    
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

## Subscription Tiers and Credit Allocation

### 1. Plan Definition

Create predefined Stripe plans with different credit allocations:

| Plan Name | Monthly Price | Initial Credits | Monthly Credits | Subscription Tier |
|-----------|--------------|----------------|----------------|-------------------|
| Free      | $0           | 10             | 10             | free              |
| Basic     | $9.99        | 100            | 50             | basic             |
| Premium   | $29.99       | 500            | 200            | premium           |
| Enterprise| $99.99       | 2000           | 1000           | enterprise        |

### 2. Tier Mapping Function

```python
def map_plan_to_subscription_tier(plan_name):
    """Map Stripe plan name to subscription tier"""
    mapping = {
        'Free Plan': 'free',
        'Basic Plan': 'basic',
        'Premium Plan': 'premium',
        'Enterprise Plan': 'enterprise',
    }
    
    # Try exact match first
    if plan_name in mapping:
        return mapping[plan_name]
    
    # Try partial match
    for key, value in mapping.items():
        if key.lower().split()[0] in plan_name.lower():
            return value
    
    # Default to basic
    return 'basic'
```

## Credit Transaction Recording

### 1. Recording Credit Allocations

When credits are allocated through Stripe subscriptions, they should be recorded in the `CreditTransaction` model:

```python
from apps.credits.models import CreditTransaction
from django.db import transaction

def allocate_subscription_credits(user, amount, description, subscription_id):
    """Allocate credits and record transaction"""
    with transaction.atomic():
        # Lock user profile to prevent race conditions
        profile = UserProfile.objects.select_for_update().get(user=user)
        old_balance = profile.credits_balance
        
        # Update credits balance
        profile.add_credits(amount)
        
        # Record transaction
        CreditTransaction.objects.create(
            user=user,
            transaction_type='addition',
            amount=amount,
            balance_after=old_balance + amount,
            description=description,
            endpoint='stripe.subscription',
            notes=f"Subscription ID: {subscription_id}"
        )
        
        return True
```

### 2. Handling Subscription Changes

When a user upgrades or downgrades their subscription, you may need to adjust their credits:

```python
def handle_subscription_change(user, old_plan, new_plan, subscription_id):
    """Handle credit changes when user changes subscription plan"""
    # Calculate credit difference for immediate allocation
    # This is a business logic decision - you might not give all initial credits on upgrade
    credit_adjustment = new_plan.initial_credits - old_plan.initial_credits
    
    if credit_adjustment > 0:
        # This is an upgrade - give additional credits
        description = f"Additional credits for upgrading to {new_plan.name}"
        allocate_subscription_credits(user, credit_adjustment, description, subscription_id)
    elif credit_adjustment < 0:
        # This is a downgrade - you might want to handle this differently
        # Options: do nothing, reduce credits, or prorate
        pass
    
    # Update user profile tier
    profile = user.profile
    profile.subscription_tier = map_plan_to_subscription_tier(new_plan.name)
    profile.save(update_fields=['subscription_tier'])
```

## Monthly Credit Allocation

### 1. Scheduled Monthly Allocation

Implement a scheduled task to allocate monthly credits to active subscribers:

```python
# management/commands/allocate_monthly_credits.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from apps.users.models import UserProfile
from apps.payments.models import StripeSubscription, StripePlan
from apps.credits.models import CreditTransaction

class Command(BaseCommand):
    help = 'Allocate monthly credits to active subscribers'
    
    def handle(self, *args, **options):
        User = get_user_model()
        today = timezone.now().date()
        
        # Get active subscriptions
        active_subscriptions = StripeSubscription.objects.filter(
            status='active',
            current_period_end__gte=timezone.now()
        )
        
        count = 0
        errors = 0
        
        for subscription in active_subscriptions:
            try:
                user = subscription.user
                profile = UserProfile.objects.get(user=user)
                
                # Skip if already allocated this month
                if profile.last_credit_allocation_date and \
                   profile.last_credit_allocation_date.month == today.month and \
                   profile.last_credit_allocation_date.year == today.year:
                    continue
                
                # Get plan and credit amount
                try:
                    plan = StripePlan.objects.get(plan_id=subscription.plan_id)
                    credit_amount = plan.monthly_credits
                    
                    if credit_amount > 0:
                        with transaction.atomic():
                            # Lock profile for update
                            profile = UserProfile.objects.select_for_update().get(user=user)
                            old_balance = profile.credits_balance
                            
                            # Add credits
                            profile.add_credits(credit_amount)
                            
                            # Update allocation date
                            profile.last_credit_allocation_date = today
                            profile.save(update_fields=['last_credit_allocation_date'])
                            
                            # Record transaction
                            CreditTransaction.objects.create(
                                user=user,
                                transaction_type='addition',
                                amount=credit_amount,
                                balance_after=old_balance + credit_amount,
                                description=f'Monthly subscription credits for {plan.name}',
                                endpoint='stripe.monthly_allocation'
                            )
                            
                            count += 1
                            self.stdout.write(f"Allocated {credit_amount} credits to user {user.username}")
                except StripePlan.DoesNotExist:
                    self.stderr.write(f"Plan not found: {subscription.plan_id}")
                    errors += 1
            except Exception as e:
                self.stderr.write(f"Error processing user {subscription.user_id}: {str(e)}")
                errors += 1
        
        self.stdout.write(self.style.SUCCESS(
            f"Monthly credits allocated to {count} users with {errors} errors"
        ))
```

### 2. Allocation on Invoice Payment

Alternatively, allocate credits when invoice payments succeed:

```python
def _handle_invoice_payment_succeeded(self, invoice):
    """Handle successful invoice payment and credit allocation"""
    # Only process subscription invoices
    if not invoice.get('subscription'):
        return
        
    # Find the subscription
    subscription_id = invoice.get('subscription')
    try:
        subscription = StripeSubscription.objects.get(subscription_id=subscription_id)
        user = subscription.user
        
        # Check if this is a renewal
        is_renewal = False
        if invoice.get('lines') and invoice.get('lines').get('data'):
            for line in invoice.get('lines').get('data'):
                if line.get('type') == 'subscription' and line.get('period'):
                    # Calculate if this is a renewal (not the first payment)
                    period_start = line.get('period').get('start')
                    is_renewal = (subscription.created_at.timestamp() < period_start)
                    break
        
        if is_renewal and subscription.plan_id:
            # If this is a renewal, allocate monthly credits
            try:
                plan = StripePlan.objects.get(plan_id=subscription.plan_id)
                if plan.monthly_credits > 0:
                    description = f"Monthly subscription credits for {plan.name}"
                    allocate_subscription_credits(
                        user, 
                        plan.monthly_credits, 
                        description, 
                        subscription_id
                    )
            except StripePlan.DoesNotExist:
                logger.error(f"Plan not found: {subscription.plan_id}")
    except StripeSubscription.DoesNotExist:
        logger.error(f"Subscription not found: {subscription_id}")
```

## Credit Balance Management

### 1. Handling Subscription Cancellation

Determine how to handle credits when a subscription is cancelled:

```python
def _handle_subscription_deleted(self, subscription):
    """Handle subscription cancellation"""
    subscription_id = subscription.get('id')
    
    try:
        stripe_subscription = StripeSubscription.objects.get(subscription_id=subscription_id)
        user = stripe_subscription.user
        
        # Update subscription status
        stripe_subscription.status = subscription.get('status')
        stripe_subscription.save(update_fields=['status'])
        
        # Update user profile
        profile = user.profile
        
        # Business decision: what to do with tier?
        # Option 1: Downgrade to free
        profile.subscription_tier = 'free'
        profile.save(update_fields=['subscription_tier'])
        
        # Business decision: what to do with remaining credits?
        # Option 1: Let them keep the credits
        # Option 2: Reset credits to free tier level
        # Option 3: Reduce credits to a maximum amount
        
        # Example of Option 2:
        # if profile.credits_balance > FREE_TIER_MAX_CREDITS:
        #     old_balance = profile.credits_balance
        #     profile.credits_balance = FREE_TIER_MAX_CREDITS
        #     profile.save(update_fields=['credits_balance'])
        #     
        #     # Record the transaction
        #     CreditTransaction.objects.create(
        #         user=user,
        #         transaction_type='deduction',
        #         amount=old_balance - FREE_TIER_MAX_CREDITS,
        #         balance_after=FREE_TIER_MAX_CREDITS,
        #         description='Credit adjustment due to subscription cancellation',
        #         endpoint='stripe.subscription.deleted'
        #     )
    except StripeSubscription.DoesNotExist:
        logger.error(f"Subscription not found: {subscription_id}")
```

### 2. Credit Usage Rate Limits

Integrate Stripe tiers with credit usage rate limits:

```python
from apps.credits.models import CreditUsageRate

def get_credit_cost_for_endpoint(endpoint_path, user):
    """Get credit cost for an endpoint based on user's subscription tier"""
    try:
        # Get base credit cost
        rate = CreditUsageRate.objects.get(endpoint_path=endpoint_path, is_active=True)
        base_cost = rate.credits_per_request
        
        # Apply tier-based discounts
        profile = user.profile
        tier_discounts = {
            'free': 1.0,     # No discount
            'basic': 0.9,    # 10% discount
            'premium': 0.7,  # 30% discount
            'enterprise': 0.5  # 50% discount
        }
        
        # Get discount multiplier, default to no discount
        discount = tier_discounts.get(profile.subscription_tier, 1.0)
        
        # Apply discount and return (minimum 1 credit)
        return max(1, int(base_cost * discount))
    except CreditUsageRate.DoesNotExist:
        # Default to 1 credit if no specific rate is defined
        return 1
```

## Implementation Examples

### 1. Creating a Subscription Checkout

```python
class CreateCheckoutSessionView(APIView):
    """Create Stripe checkout session for subscription purchase"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Get the plan ID from the request
        plan_id = request.data.get('plan_id')
        
        try:
            # Validate plan exists
            plan = StripePlan.objects.get(id=plan_id, active=True)
            
            # Get or create Stripe customer
            stripe_customer, created = StripeCustomer.objects.get_or_create(
                user=request.user,
                defaults={
                    'customer_id': self._create_stripe_customer(request.user)
                }
            )
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                customer=stripe_customer.customer_id,
                payment_method_types=['card'],
                line_items=[
                    {
                        'price': plan.plan_id,  # Stripe price ID
                        'quantity': 1,
                    },
                ],
                mode='subscription',
                success_url=request.build_absolute_uri(
                    reverse('subscription-success')
                ) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=request.build_absolute_uri(
                    reverse('subscription-cancel')
                ),
            )
            
            return Response({
                'checkout_url': session.url,
                'session_id': session.id
            })
            
        except StripePlan.DoesNotExist:
            return Response(
                {'error': 'Invalid plan selected'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except stripe.error.StripeError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _create_stripe_customer(self, user):
        """Create a Stripe customer for the user"""
        customer = stripe.Customer.create(
            email=user.email,
            name=f"{user.first_name} {user.last_name}".strip() or user.username,
            metadata={
                'user_id': str(user.id),
                'username': user.username
            }
        )
        return customer.id
```

### 2. Subscription Success Handler

```python
class SubscriptionSuccessView(APIView):
    """Handle successful subscription checkout"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response(
                {'error': 'No session ID provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Retrieve the session from Stripe
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            subscription_id = checkout_session.subscription
            
            if not subscription_id:
                return Response(
                    {'error': 'No subscription found in session'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Process the subscription
            self._process_subscription(request.user, subscription_id)
            
            return Response({
                'status': 'subscription_active',
                'subscription_id': subscription_id
            })
            
        except stripe.error.StripeError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _process_subscription(self, user, subscription_id):
        """Process a new subscription"""
        from apps.credits.models import CreditTransaction
        
        with transaction.atomic():
            # Retrieve subscription details
            stripe_subscription = stripe.Subscription.retrieve(subscription_id)
            plan_id = stripe_subscription['items']['data'][0]['plan']['id']
            
            # Get or create local plan
            plan, created = StripePlan.objects.get_or_create(
                plan_id=plan_id,
                defaults={
                    'name': stripe_subscription['items']['data'][0]['plan'].get('nickname', 'Unknown Plan'),
                    'amount': stripe_subscription['items']['data'][0]['plan'].get('amount', 0),
                    'currency': stripe_subscription['items']['data'][0]['plan'].get('currency', 'usd'),
                    'interval': stripe_subscription['items']['data'][0]['plan'].get('interval', 'month')
                    # Set default credits values - you'd want to update these manually
                }
            )
            
            # Create subscription record
            subscription = StripeSubscription.objects.create(
                user=user,
                subscription_id=subscription_id,
                status=stripe_subscription['status'],
                plan_id=plan_id,
                current_period_start=datetime.fromtimestamp(stripe_subscription['current_period_start']),
                current_period_end=datetime.fromtimestamp(stripe_subscription['current_period_end']),
                cancel_at_period_end=stripe_subscription.get('cancel_at_period_end', False)
            )
            
            # Update user profile
            profile = UserProfile.objects.select_for_update().get(user=user)
            old_tier = profile.subscription_tier
            new_tier = self._map_plan_to_tier(plan.name)
            
            profile.subscription_tier = new_tier
            profile.save(update_fields=['subscription_tier'])
            
            # Allocate initial credits
            if plan.initial_credits > 0:
                old_balance = profile.credits_balance
                profile.add_credits(plan.initial_credits)
                
                # Create credit transaction record
                CreditTransaction.objects.create(
                    user=user,
                    transaction_type='addition',
                    amount=plan.initial_credits,
                    balance_after=old_balance + plan.initial_credits,
                    description=f'Initial subscription credits for {plan.name}',
                    endpoint='stripe.subscription.created'
                )
```

### 3. Credit-Based View Integration

Integrate with your existing credit-based view system:

```python
from apps.users.views.creditable_views.utility_view import call_function_with_credits
from apps.payments.models import StripeSubscription

class SubscriptionAwareAPIView(APIView):
    """API view that considers subscription tier for credit cost"""
    permission_classes = [IsAuthenticated]
    
    def get_credit_cost(self, request):
        """Get credit cost based on subscription tier"""
        base_cost = 5  # Default cost
        
        # Check if user has active subscription
        try:
            subscription = StripeSubscription.objects.filter(
                user=request.user,
                status='active'
            ).first()
            
            if subscription:
                # Apply tier discounts
                plan = StripePlan.objects.get(plan_id=subscription.plan_id)
                tier_discounts = {
                    'basic': 0.9,    # 10% discount
                    'premium': 0.7,  # 30% discount
                    'enterprise': 0.5  # 50% discount
                }
                
                tier = self._map_plan_to_tier(plan.name)
                discount = tier_discounts.get(tier, 1.0)
                
                # Apply discount (minimum 1 credit)
                return max(1, int(base_cost * discount))
        except Exception:
            pass
        
        return base_cost
    
    def get(self, request, *args, **kwargs):
        # Use the utility function with dynamic credit cost
        return call_function_with_credits(
            self.perform_get,
            request,
            credit_cost=self.get_credit_cost(request)
        )
    
    def perform_get(self, request):
        """Implement this method in subclasses"""
        raise NotImplementedError("Subclasses must implement perform_get")
```
