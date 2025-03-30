from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch, MagicMock
from apps.stripe_home.models import StripeCustomer, StripePlan, StripeSubscription
from apps.stripe_home.views import StripeWebhookView
from apps.users.models import UserProfile
import uuid

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
        if not hasattr(self.user, 'profile'):
            # Create a real UserProfile instance
            UserProfile.objects.create(
                user=self.user,
                supabase_uid=f'test-{uuid.uuid4()}',
                credits_balance=0,
                subscription_tier='free'
            )
        else:
            # Reset credits balance if profile exists
            self.user.profile.credits_balance = 0
            self.user.profile.save()
        
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
    
    @patch('apps.stripe_home.views.get_stripe_client')
    def test_initial_credit_allocation(self, mock_get_stripe_client):
        """Test allocating initial credits when subscription is created"""
        # Mock the stripe client
        mock_stripe_client = MagicMock()
        mock_get_stripe_client.return_value = mock_stripe_client
        
        # Initial balance should be 0
        self.assertEqual(self.user.profile.credits_balance, 0)
        
        # Create a mock subscription
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
        
        # Call the actual handler method - this should call the real allocate_subscription_credits function
        self.webhook_handler._handle_subscription_created(mock_subscription, mock_stripe_client)
        
        # Refresh user from DB
        self.user.refresh_from_db()
        
        # Verify credits were added to the user's account
        self.assertEqual(
            self.user.profile.credits_balance,
            self.plan.initial_credits,
            f"User should have {self.plan.initial_credits} credits after subscription creation"
        )
    
    @patch('apps.stripe_home.views.get_stripe_client')
    def test_monthly_credit_allocation(self, mock_get_stripe_client):
        """Test allocating monthly credits when invoice payment succeeds"""
        # Mock the stripe client
        mock_stripe_client = MagicMock()
        mock_get_stripe_client.return_value = mock_stripe_client
        
        # Initial balance should be 0
        self.assertEqual(self.user.profile.credits_balance, 0)
        
        # Create a subscription in the database
        # This is needed because the webhook handler looks for an existing subscription
        StripeSubscription.objects.create(
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
        
        # Call the actual handler method - this should call the real allocate_subscription_credits function
        self.webhook_handler._handle_invoice_payment_succeeded(mock_invoice, mock_stripe_client)
        
        # Refresh user from DB
        self.user.refresh_from_db()
        
        # Verify credits were added to the user's account
        self.assertEqual(
            self.user.profile.credits_balance,
            self.plan.monthly_credits,
            f"User should have {self.plan.monthly_credits} credits after invoice payment"
        )
