from django.db import transaction
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

def allocate_subscription_credits(user, amount, description, subscription_id):
    """
    Allocate credits to a user and record the transaction.
    
    Args:
        user: The user who receives the credits
        amount: Number of credits to add
        description: Description of the credit allocation
        subscription_id: Stripe subscription ID for reference
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Import here to avoid circular imports
    from apps.users.models import UserProfile
    
    try:
        # Check if user has a profile
        if not hasattr(user, 'profile'):
            logger.error(f"User {user.id} has no profile for credit allocation")
            return False
        
        profile = user.profile
        
        with transaction.atomic():
            # Lock the profile to prevent race conditions
            profile = UserProfile.objects.select_for_update().get(id=profile.id)
            old_balance = profile.credits_balance
            
            # Add credits to the user's balance
            profile.add_credits(amount)
            profile.last_credit_allocation_date = timezone.now()
            profile.save()
            
            # Record the transaction if CreditTransaction model is available
            try:
                from apps.credits.models import CreditTransaction
                
                # Create transaction record
                CreditTransaction.objects.create(
                    user=user,
                    transaction_type='addition',
                    amount=amount,
                    balance_after=old_balance + amount,
                    description=description,
                    endpoint='stripe.subscription',
                    notes=f"Subscription ID: {subscription_id}"
                )
                
                logger.info(f"Added {amount} credits to user {user.id} for subscription {subscription_id}")
            except ImportError:
                logger.warning("CreditTransaction model not available, skipping transaction recording")
        
        return True
    
    except Exception as e:
        logger.error(f"Error allocating subscription credits: {str(e)}")
        return False


def map_plan_to_subscription_tier(plan_name):
    """
    Map Stripe plan name to subscription tier.
    
    Args:
        plan_name: Name of the Stripe plan
        
    Returns:
        str: Subscription tier name (free, basic, premium, enterprise)
    """
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


def handle_subscription_change(user, old_plan, new_plan, subscription_id):
    """
    Handle credit changes when user changes subscription plan.
    
    Args:
        user: The user changing plans
        old_plan: Previous StripePlan instance
        new_plan: New StripePlan instance
        subscription_id: Stripe subscription ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Calculate credit difference for immediate allocation
    credit_adjustment = new_plan.initial_credits - old_plan.initial_credits
    
    if credit_adjustment > 0:
        # This is an upgrade - give additional credits
        description = f"Additional credits for upgrading to {new_plan.name}"
        success = allocate_subscription_credits(user, credit_adjustment, description, subscription_id)
    elif credit_adjustment < 0:
        # This is a downgrade - typically no action needed for credits
        # You could implement credit reduction here if that's part of your business logic
        success = True
    else:
        # No change in initial credits
        success = True
    
    # Update user profile subscription tier if successful
    if success and hasattr(user, 'profile'):
        profile = user.profile
        profile.subscription_tier = map_plan_to_subscription_tier(new_plan.name)
        profile.save(update_fields=['subscription_tier'])
    
    return success
