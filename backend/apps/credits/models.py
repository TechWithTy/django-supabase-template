from django.db import models, transaction
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
import logging
import uuid
from typing import Optional

logger = logging.getLogger("credits")

class CreditTransaction(models.Model):
    """
    Model to track credit transactions for users.
    
    This model records all credit transactions (additions and deductions)
    for audit and tracking purposes.
    """
    TRANSACTION_TYPE_CHOICES = [
        ('deduction', _('Deduction')),
        ('addition', _('Addition')),
        ('hold', _('Hold')),
        ('release', _('Hold Release')),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='credit_transactions'
    )
    transaction_type = models.CharField(
        _('Transaction Type'),
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        default='deduction'
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
    reference_id = models.UUIDField(
        _('Reference ID'),
        null=True,
        blank=True,
        help_text=_('Reference to related transaction (e.g., hold ID)')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Credit Transaction')
        verbose_name_plural = _('Credit Transactions')
        ordering = ['-created_at']
    
    def __str__(self) -> str:
        return f"{self.user.username}: {self.amount} credits ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    def save(self, *args, **kwargs):
        # Log the transaction details for audit purposes
        is_new = self._state.adding
        super().save(*args, **kwargs)
        
        if is_new:
            log_level = logging.INFO
            if self.transaction_type == 'deduction' and self.amount > 10:
                log_level = logging.WARNING
                
            logger.log(
                log_level,
                "Credit transaction: %s",
                {
                    "transaction_id": str(self.id),
                    "user_id": self.user.id,
                    "username": self.user.username,
                    "type": self.transaction_type,
                    "amount": self.amount,
                    "balance_after": self.balance_after,
                    "endpoint": self.endpoint,
                    "reference_id": str(self.reference_id) if self.reference_id else None
                }
            )


class CreditHold(models.Model):
    """
    Model to track credit holds for long-running operations.
    
    This model allows for placing a hold on credits before an operation begins,
    and either converting the hold to a deduction or releasing the hold based on
    the operation outcome.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='credit_holds'
    )
    amount = models.IntegerField(
        _('Amount'),
        help_text=_('Number of credits on hold')
    )
    description = models.CharField(
        _('Description'),
        max_length=255,
        help_text=_('Description of the operation requiring the hold')
    )
    endpoint = models.CharField(
        _('API Endpoint'),
        max_length=255,
        blank=True,
        null=True,
        help_text=_('API endpoint that triggered the hold')
    )
    is_active = models.BooleanField(
        _('Is Active'),
        default=True,
        help_text=_('Whether this hold is still active')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(
        _('Expires At'),
        null=True,
        blank=True,
        help_text=_('When this hold automatically expires')
    )
    
    class Meta:
        verbose_name = _('Credit Hold')
        verbose_name_plural = _('Credit Holds')
        ordering = ['-created_at']
    
    def __str__(self) -> str:
        status = "Active" if self.is_active else "Released"
        return f"{self.user.username}: {self.amount} credits on hold ({status})"

    @classmethod
    @transaction.atomic
    def place_hold(cls, user, amount: int, description: str, endpoint: Optional[str] = None) -> Optional['CreditHold']:
        """
        Place a hold on user credits for a pending operation.
        
        Returns the CreditHold if successful, None if insufficient credits.
        """
        from apps.users.models import UserProfile
        
        try:
            # Lock the user profile row
            profile = UserProfile.objects.select_for_update().get(user=user)
            
            # Check if user has sufficient credits
            if profile.credits_balance < amount:
                logger.warning(
                    "Insufficient credits for hold: %s", 
                    {"user_id": user.id, "amount": amount, "balance": profile.credits_balance}
                )
                return None
            
            # Create the hold record
            hold = cls.objects.create(
                user=user,
                amount=amount,
                description=description,
                endpoint=endpoint
            )
            
            # Reduce available balance but don't deduct yet
            profile.credits_balance -= amount
            profile.save(update_fields=['credits_balance', 'updated_at'])
            
            # Record the transaction
            CreditTransaction.objects.create(
                id=uuid.uuid4(),
                user=user,
                transaction_type='hold',
                amount=-amount,  # negative amount for hold
                balance_after=profile.credits_balance,
                description=f"Hold: {description}",
                endpoint=endpoint,
                reference_id=hold.id
            )
            
            logger.info(
                "Credit hold placed: %s",
                {"hold_id": str(hold.id), "user_id": user.id, "amount": amount}
            )
            
            return hold
            
        except UserProfile.DoesNotExist:
            logger.error("User profile not found for credit hold: %s", {"user_id": user.id})
            return None
        except Exception as e:
            logger.exception("Error placing credit hold: %s", {"user_id": user.id, "error": str(e)})
            return None
    
    @transaction.atomic
    def commit(self) -> bool:
        """
        Commit the hold, converting it to a permanent deduction.
        
        Returns True if successful, False otherwise.
        """
        if not self.is_active:
            logger.warning("Attempting to commit an inactive hold: %s", {"hold_id": str(self.id)})
            return False
        
        try:
            # Mark the hold as inactive
            self.is_active = False
            self.save(update_fields=['is_active', 'updated_at'])
            
            # Record the deduction transaction
            CreditTransaction.objects.create(
                id=uuid.uuid4(),
                user=self.user,
                transaction_type='deduction',
                amount=0,  # 0 because the balance already reflects the deduction
                balance_after=self.user.profile.credits_balance,
                description=f"Confirmed: {self.description}",
                endpoint=self.endpoint,
                reference_id=self.id
            )
            
            logger.info(
                "Credit hold committed: %s",
                {"hold_id": str(self.id), "user_id": self.user.id, "amount": self.amount}
            )
            
            return True
            
        except Exception as e:
            logger.exception("Error committing credit hold: %s", {"hold_id": str(self.id), "error": str(e)})
            return False
    
    @transaction.atomic
    def release(self) -> bool:
        """
        Release the hold, returning credits to the user's balance.
        
        Returns True if successful, False otherwise.
        """
        if not self.is_active:
            logger.warning("Attempting to release an inactive hold: %s", {"hold_id": str(self.id)})
            return False
        
        try:
            from apps.users.models import UserProfile
            
            # Lock the user profile row
            profile = UserProfile.objects.select_for_update().get(user=self.user)
            
            # Restore credits to user's balance
            profile.credits_balance += self.amount
            profile.save(update_fields=['credits_balance', 'updated_at'])
            
            # Mark the hold as inactive
            self.is_active = False
            self.save(update_fields=['is_active', 'updated_at'])
            
            # Record the release transaction
            CreditTransaction.objects.create(
                id=uuid.uuid4(),
                user=self.user,
                transaction_type='release',
                amount=self.amount,  # positive amount for release
                balance_after=profile.credits_balance,
                description=f"Released: {self.description}",
                endpoint=self.endpoint,
                reference_id=self.id
            )
            
            logger.info(
                "Credit hold released: %s",
                {"hold_id": str(self.id), "user_id": self.user.id, "amount": self.amount}
            )
            
            return True
            
        except UserProfile.DoesNotExist:
            logger.error("User profile not found for credit hold release: %s", {"hold_id": str(self.id)})
            return False
        except Exception as e:
            logger.exception("Error releasing credit hold: %s", {"hold_id": str(self.id), "error": str(e)})
            return False


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
