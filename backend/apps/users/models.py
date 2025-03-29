from django.db import models, transaction
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import uuid

class UserProfile(models.Model):
    """
    Extended user profile model to store additional user information.
    
    This model extends the built-in Django User model with additional fields
    that are specific to our application, including Supabase-related information.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_('Unique identifier for the profile')
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='profile'
    )
    supabase_uid = models.CharField(
        _('Supabase UID'),
        max_length=255,
        unique=True,
        help_text=_('Unique identifier from Supabase')
    )
    subscription_tier = models.CharField(
        _('Subscription Tier'),
        max_length=50,
        default='free',
        choices=[
            ('free', _('Free')),
            ('basic', _('Basic')),
            ('premium', _('Premium')),
            ('enterprise', _('Enterprise')),
        ],
        help_text=_('User subscription level')
    )
    credits_balance = models.IntegerField(
        _('Credits Balance'),
        default=0,
        help_text=_('Available API credits')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('User Profile')
        verbose_name_plural = _('User Profiles')
    
    def __str__(self) -> str:
        return f"{self.user.username}'s profile"
    
    def get_subscription_rate_limit(self) -> str:
        """
        Get the rate limit based on the user's subscription tier.
        """
        limits = {
            'free': '100/day',
            'basic': '1000/day',
            'premium': '5000/day',
            'enterprise': '10000/day',
        }
        return limits.get(self.subscription_tier, '100/day')
    
    def has_sufficient_credits(self, required_credits: int) -> bool:
        """
        Check if the user has sufficient credits for an operation.
        """
        return self.credits_balance >= required_credits
    
    @transaction.atomic
    def deduct_credits(self, amount: int) -> bool:
        """
        Deduct credits from the user's balance with transaction safety.
        
        Uses select_for_update to lock the row during transaction, preventing race conditions
        when multiple requests attempt to deduct credits simultaneously.
        
        Returns True if successful, False if insufficient credits.
        """
        # Get fresh data with select_for_update to prevent race conditions
        user_profile = UserProfile.objects.select_for_update().get(id=self.id)
        
        if user_profile.has_sufficient_credits(amount):
            user_profile.credits_balance -= amount
            user_profile.save(update_fields=['credits_balance', 'updated_at'])
            
            # Update current instance to match database state
            self.credits_balance = user_profile.credits_balance
            self.updated_at = user_profile.updated_at
            
            return True
        return False
    
    @transaction.atomic
    def add_credits(self, amount: int) -> None:
        """
        Add credits to the user's balance with transaction safety.
        
        Uses select_for_update to lock the row during transaction, preventing race conditions
        when multiple operations might modify the credit balance simultaneously.
        """
        # Get fresh data with select_for_update to prevent race conditions
        user_profile = UserProfile.objects.select_for_update().get(id=self.id)
        
        user_profile.credits_balance += amount
        user_profile.save(update_fields=['credits_balance', 'updated_at'])
        
        # Update current instance to match database state
        self.credits_balance = user_profile.credits_balance
        self.updated_at = user_profile.updated_at
