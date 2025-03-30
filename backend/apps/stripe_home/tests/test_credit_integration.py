from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch, MagicMock
from ..models import StripeCustomer, StripeSubscription, StripePlan
from ..views import StripeWebhookView

User = get_user_model()

class StripeCreditIntegrationTest(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create user profile if it doesn't exist
        # This assumes there's a UserProfile model with a credits_balance field
        if hasattr(self.user, 'profile'):
            self.user.profile.credits_balance = 0
            self.user.profile.save()
        else:
            # Mock profile if it doesn't exist for testing
            self.user.profile = MagicMock()
            self.user.profile.credits_balance = 0
            self.user.profile.add_credits = lambda x: setattr(self.user.profile, 'credits_balance', 
                                                             self.user.profile.credits_balance + x)
        
        # Create test plan with credits
        self.plan = StripePlan.objects.create(
            plan_id='price_123456',
            name='Test Plan',
            amount=1999,  # $19.99
            currency='usd',
            interval='month',
            initial_credits=100,
            monthly_credits=50,
            active=True,
            livemode=False
        )
        
        # Create test customer
        self.customer = StripeCustomer.objects.create(
            user=self.user,
            customer_id='cus_123456',
            livemode=False
        )
        
        # Create webhook handler
        self.webhook_handler = StripeWebhookView()
    
    @patch('apps.stripe_home.credit.allocate_subscription_credits')
    @patch('stripe.StripeClient')
    def test_initial_credit_allocation(self, mock_stripe_client, mock_allocate_credits):
        """Test allocating initial credits when subscription is created"""
        # Mock subscription object
        mock_subscription = MagicMock()
        mock_subscription.id = 'sub_123456'
        mock_subscription.customer = 'cus_123456'
        mock_subscription.status = 'active'
        mock_subscription.current_period_start = int(timezone.now().timestamp())
        mock_subscription.current_period_end = int((timezone.now() + timezone.timedelta(days=30)).timestamp())
        mock_subscription.cancel_at_period_end = False
        mock_subscription.livemode = False
        
        # Mock subscription items
        mock_item = MagicMock()
        mock_item.price.id = self.plan.plan_id
        mock_subscription.items.data = [mock_item]
        
        # Call the handler method
        self.webhook_handler._handle_subscription_created(mock_subscription, mock_stripe_client)
        
        # Verify credit allocation was called with correct parameters
        mock_allocate_credits.assert_called_once_with(
            user=self.user,
            amount=self.plan.initial_credits,
            description=f"Initial credits for {self.plan.name} subscription",
            subscription_id='sub_123456'
        )
    
    @patch('apps.stripe_home.credit.allocate_subscription_credits')
    @patch('stripe.StripeClient')
    def test_monthly_credit_allocation(self, mock_stripe_client, mock_allocate_credits):
        """Test allocating monthly credits when invoice payment succeeds"""
        # Create a subscription
        subscription = StripeSubscription.objects.create(
            user=self.user,
            subscription_id='sub_123456',
            status='active',
            plan_id=self.plan.plan_id,
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timezone.timedelta(days=30),
            cancel_at_period_end=False,
            livemode=False
        )
        
        # Mock invoice object
        mock_invoice = MagicMock()
        mock_invoice.id = 'in_123456'
        mock_invoice.customer = 'cus_123456'
        mock_invoice.subscription = 'sub_123456'
        mock_invoice.status = 'paid'
        
        # Call the handler method
        self.webhook_handler._handle_invoice_payment_succeeded(mock_invoice, mock_stripe_client)
        
        # Verify credit allocation was called with correct parameters
        mock_allocate_credits.assert_called_once_with(
            user=self.user,
            amount=self.plan.monthly_credits,
            description=f"Monthly credits for {self.plan.name} subscription",
            subscription_id='sub_123456'
        )
