from typing import Optional, Any, Dict
import re

from django.core.cache import cache
from rest_framework.throttling import UserRateThrottle
from rest_framework.request import Request

from apps.users.models import UserProfile
from .models import CreditUsageRate, CreditTransaction

class CreditBasedThrottle(UserRateThrottle):
    """
    Custom throttle that limits requests based on user's subscription tier and credits.
    
    This throttle checks if the user has sufficient credits for the requested operation
    and deducts credits accordingly. It also enforces rate limits based on the user's
    subscription tier.
    """
    scope = 'user'  # Default scope
    
    def get_cache_key(self, request: Request, view: Any) -> Optional[str]:
        """
        Get a unique cache key for the current request based on the user.
        """
        if request.user.is_authenticated:
            # Try to get the user profile
            try:
                profile = UserProfile.objects.get(user=request.user)
                # Use the subscription tier to determine the throttle scope
                self.scope = profile.subscription_tier
            except UserProfile.DoesNotExist:
                # If no profile exists, use the default scope
                pass
                
        return super().get_cache_key(request, view)
    
    def allow_request(self, request: Request, view: Any) -> bool:
        """
        Check if the request should be allowed based on rate limits and credit balance.
        
        This method first checks if the user has exceeded their rate limit, then
        checks if they have sufficient credits for the operation.
        """
        # Anonymous users are subject to standard rate limiting
        if not request.user.is_authenticated:
            return super().allow_request(request, view)
        
        # Staff and superusers bypass throttling
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check rate limiting based on subscription tier
        rate_limited = not super().allow_request(request, view)
        if rate_limited:
            return False
        
        # Check if the endpoint requires credits
        credits_required = self._get_required_credits(request)
        if credits_required <= 0:
            return True
        
        # Check if the user has sufficient credits
        try:
            profile, created = UserProfile.objects.get_or_create(
                user=request.user,
                defaults={'supabase_uid': request.user.username}
            )
            
            if not profile.has_sufficient_credits(credits_required):
                return False
            
            # Deduct credits and record the transaction
            profile.deduct_credits(credits_required)
            
            # Record the credit transaction
            CreditTransaction.objects.create(
                user=request.user,
                amount=-credits_required,
                balance_after=profile.credits_balance,
                description=f"API request to {request.path}",
                endpoint=request.path
            )
            
            return True
            
        except Exception as e:
            # Log the error and allow the request (fail open)
            print(f"Error checking credits: {str(e)}")
            return True
    
    def _get_required_credits(self, request: Request) -> int:
        """
        Determine the number of credits required for the current request.
        
        This method checks the CreditUsageRate model to find a matching endpoint
        pattern and returns the corresponding credit cost.
        """
        path = request.path
        
        # Get all active credit usage rates
        credit_rates = CreditUsageRate.objects.filter(is_active=True)
        
        # Find the first matching endpoint pattern
        for rate in credit_rates:
            pattern = rate.endpoint_path
            # Convert the endpoint pattern to a regex pattern
            # Replace {id} or similar placeholders with regex groups
            regex_pattern = pattern.replace('/', r'\/')
            regex_pattern = re.sub(r'\{[^}]+\}', r'[^\/]+', regex_pattern)
            
            if re.match(regex_pattern, path):
                return rate.credits_per_request
        
        # Default to 0 credits if no matching pattern is found
        return 0
