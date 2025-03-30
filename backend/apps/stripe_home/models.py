from django.db import models
from django.conf import settings

class StripeCustomer(models.Model):
    """Link between Django user and Stripe customer"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    customer_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    livemode = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.username} ({self.customer_id})"
    
    def get_dashboard_url(self):
        """Get URL to view this customer in Stripe dashboard"""
        if self.livemode:
            return f"https://dashboard.stripe.com/customers/{self.customer_id}"
        return f"https://dashboard.stripe.com/test/customers/{self.customer_id}"
    
    class Meta:
        app_label = 'stripe_home'


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
    
    def __str__(self):
        return f"{self.name} ({self.currency} {self.amount/100:.2f}/{self.interval})"
    
    class Meta:
        app_label = 'stripe_home'


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
    
    def __str__(self):
        return f"{self.user.username}'s {self.status} subscription ({self.subscription_id})"
    
    def get_dashboard_url(self):
        """Get URL to view this subscription in Stripe dashboard"""
        if self.livemode:
            return f"https://dashboard.stripe.com/subscriptions/{self.subscription_id}"
        return f"https://dashboard.stripe.com/test/subscriptions/{self.subscription_id}"
    
    class Meta:
        app_label = 'stripe_home'
