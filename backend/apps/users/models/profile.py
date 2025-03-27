from django.conf import settings
from django.db import models



# The Profile model extends the default user model with additional fields for AI-enabled features
# and credit management. This ensures that each user can have unique AI-related settings and credit balance.

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(max_length=50, blank=True, null=True, help_text="User's first name")
    last_name = models.CharField(max_length=50, blank=True, null=True, help_text="User's last name")
    email = models.EmailField(blank=True, null=True, help_text="User's email address")
    phone_number = models.CharField(max_length=20, blank=True, null=True, help_text="User's contact phone number")
    source = models.CharField(max_length=100, blank=True, null=True, help_text="Signup source or context")
    contextual_info = models.TextField(blank=True, null=True, help_text="Additional contextual information for business prompting")
    ai_enabled = models.BooleanField(default=False, help_text='Enable AI features for the user')
    credits = models.PositiveIntegerField(default=0, help_text='Credit balance for AI execution')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.user.username}"



# The CreditTransaction model records credit transactions related to AI usage. 
# This allows for tracking and auditing credit usages or additions over time.

class CreditTransaction(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='transactions')
    amount = models.IntegerField(help_text='Amount of credits deducted (negative) or added (positive)')
    description = models.TextField(blank=True, null=True, help_text='Reason for this transaction')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transaction of {self.amount} for {self.profile.user.username} at {self.created_at}"
