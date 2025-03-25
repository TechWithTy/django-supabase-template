from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class CreditTransaction(models.Model):
    """
    Model to track credit transactions for users.
    
    This model records all credit transactions (additions and deductions)
    for audit and tracking purposes.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='credit_transactions'
    )
    amount = models.IntegerField(
        _('Amount'),
        help_text=_('Positive for additions, negative for deductions')
    )
    balance_after = models.IntegerField(
        _('Balance After Transaction'),
        help_text=_('User balance after this transaction')
    )
    description = models.CharField(
        _('Description'),
        max_length=255,
        help_text=_('Description of the transaction')
    )
    endpoint = models.CharField(
        _('API Endpoint'),
        max_length=255,
        blank=True,
        null=True,
        help_text=_('API endpoint that triggered the transaction')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Credit Transaction')
        verbose_name_plural = _('Credit Transactions')
        ordering = ['-created_at']
    
    def __str__(self) -> str:
        return f"{self.user.username}: {self.amount} credits ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

class CreditUsageRate(models.Model):
    """
    Model to define credit usage rates for different API endpoints.
    
    This model allows administrators to set different credit costs
    for different API endpoints or operations.
    """
    endpoint_path = models.CharField(
        _('Endpoint Path'),
        max_length=255,
        unique=True,
        help_text=_('API endpoint path pattern (e.g., /api/resource/)')
    )
    credits_per_request = models.IntegerField(
        _('Credits Per Request'),
        default=1,
        help_text=_('Number of credits deducted per request')
    )
    description = models.TextField(
        _('Description'),
        blank=True,
        help_text=_('Description of the endpoint and its credit usage')
    )
    is_active = models.BooleanField(
        _('Is Active'),
        default=True,
        help_text=_('Whether this credit usage rate is active')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Credit Usage Rate')
        verbose_name_plural = _('Credit Usage Rates')
    
    def __str__(self) -> str:
        return f"{self.endpoint_path}: {self.credits_per_request} credits"
