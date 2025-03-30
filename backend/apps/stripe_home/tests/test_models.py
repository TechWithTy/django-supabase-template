from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.stripe_home.models import StripeCustomer, StripeSubscription, StripePlan

User = get_user_model()

class StripeModelTests(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create test plan
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
        
        # Create test subscription
        self.subscription = StripeSubscription.objects.create(
            user=self.user,
            subscription_id='sub_123456',
            status='active',
            plan_id=self.plan.plan_id,
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timezone.timedelta(days=30),
            cancel_at_period_end=False,
            livemode=False
        )
    
    def test_stripe_customer_model(self):
        """Test StripeCustomer model"""
        customer = StripeCustomer.objects.get(id=self.customer.id)
        self.assertEqual(customer.user, self.user)
        self.assertEqual(customer.customer_id, 'cus_123456')
        self.assertEqual(customer.livemode, False)
        self.assertIsNotNone(customer.created_at)
        self.assertIsNotNone(customer.updated_at)
        
        # Test dashboard URL method
        self.assertEqual(
            customer.get_dashboard_url(),
            f"https://dashboard.stripe.com/test/customers/{customer.customer_id}"
        )
    
    def test_stripe_plan_model(self):
        """Test StripePlan model"""
        plan = StripePlan.objects.get(id=self.plan.id)
        self.assertEqual(plan.plan_id, 'price_123456')
        self.assertEqual(plan.name, 'Test Plan')
        self.assertEqual(plan.amount, 1999)
        self.assertEqual(plan.currency, 'usd')
        self.assertEqual(plan.interval, 'month')
        self.assertEqual(plan.initial_credits, 100)
        self.assertEqual(plan.monthly_credits, 50)
        self.assertEqual(plan.active, True)
        self.assertEqual(plan.livemode, False)
    
    def test_stripe_subscription_model(self):
        """Test StripeSubscription model"""
        subscription = StripeSubscription.objects.get(id=self.subscription.id)
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.subscription_id, 'sub_123456')
        self.assertEqual(subscription.status, 'active')
        self.assertEqual(subscription.plan_id, 'price_123456')
        self.assertIsNotNone(subscription.current_period_start)
        self.assertIsNotNone(subscription.current_period_end)
        self.assertEqual(subscription.cancel_at_period_end, False)
        self.assertEqual(subscription.livemode, False)
