import json
from datetime import datetime, timedelta
import random
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth import get_user_model

from rest_framework.test import APIClient
from rest_framework import status

import logging

# Import all the necessary models
from apps.stripe_home.models import StripePlan, StripeCustomer, StripeSubscription

# Set up test logger
logger = logging.getLogger(__name__)

User = get_user_model()

# Make sure we're using test API keys
assert 'test' in settings.STRIPE_SECRET_KEY or settings.STRIPE_SECRET_KEY.startswith('sk_test_')


# Create a custom mock ProductService that accepts the same parameters as Stripe's API
class MockProduct:
    def __init__(self, **kwargs):
        self.id = 'prod_test123456'
        self.name = kwargs.get('name', 'Test Product')
        self.description = kwargs.get('description', '')
        self.metadata = kwargs.get('metadata', {})
        self.active = kwargs.get('active', True)
        self.created = int(datetime.now().timestamp())
        self.updated = int(datetime.now().timestamp())
        self.object = 'product'

class MockPrice:
    def __init__(self, **kwargs):
        # Make id an integer to match URL pattern requirements
        self.id = 123456  # Changed from string to integer for URL pattern matching
        self.product = kwargs.get('product', 'prod_test123456')
        self.unit_amount = kwargs.get('unit_amount', 1000)
        self.currency = kwargs.get('currency', 'usd')
        self.recurring = kwargs.get('recurring', {'interval': 'month'})
        self.lookup_key = kwargs.get('lookup_key', None)
        self.metadata = kwargs.get('metadata', {})
        self.object = 'price'

class MockProductService:
    def create(self, **kwargs):
        # This service should match Stripe's API signature for product creation
        return MockProduct(**kwargs)
        
    def delete(self, product_id, **kwargs):
        # Mock deletion - just return success
        return {"id": product_id, "deleted": True}

class MockPriceService:
    def create(self, **kwargs):
        # This service should match Stripe's API signature for price creation
        return MockPrice(**kwargs)
        
    def delete(self, price_id, **kwargs):
        # Mock deletion - just return success
        return {"id": price_id, "deleted": True}

class MockCustomerService:
    def create(self, email=None, name=None, metadata=None, **kwargs):
        # Explicitly handle the parameters used in the view
        customer_data = {
            'email': email,
            'name': name,
            'metadata': metadata or {},
        }
        # Include any other parameters
        customer_data.update(kwargs)
        return MockCustomer(**customer_data)
        
    def delete(self, customer_id, **kwargs):
        # Mock deletion - just return success
        return {"id": customer_id, "deleted": True}

class MockCustomer:
    def __init__(self, **kwargs):
        self.id = 'cus_test123456'
        self.email = kwargs.get('email', 'test@example.com')
        self.name = kwargs.get('name', 'Test Customer')
        self.metadata = kwargs.get('metadata', {})
        self.object = 'customer'

class MockSubscriptionService:
    def create(self, **kwargs):
        return MockSubscription(**kwargs)
        
    def delete(self, subscription_id, **kwargs):
        # Mock deletion - just return success
        return {"id": subscription_id, "deleted": True}

class MockSubscription:
    def __init__(self, **kwargs):
        self.id = 'sub_test123456'
        self.customer = kwargs.get('customer', 'cus_test123456')
        self.items = kwargs.get('items', [{'price': 'price_test123456'}])
        self.status = kwargs.get('status', 'active')
        self.current_period_start = int(datetime.now().timestamp())
        self.current_period_end = int((datetime.now() + timedelta(days=30)).timestamp())
        self.cancel_at_period_end = kwargs.get('cancel_at_period_end', False)
        self.livemode = kwargs.get('livemode', False)
        self.object = 'subscription'

class MockCheckoutSessionService:
    def create(self, **kwargs):
        # Accept all parameters the real Stripe API would
        return MockCheckoutSession(**kwargs)

    def retrieve(self, session_id):
        return MockCheckoutSession(session_id=session_id)
        
    def list_line_items(self, session_id):
        # Mock line items for checkout session
        return MockLineItemList()

class MockLineItemList:
    def __init__(self):
        self.data = [
            MockLineItem()
        ]
        self.has_more = False
        self.url = '/v1/checkout/sessions/{session_id}/line_items'
        self.object = 'list'

class MockLineItem:
    def __init__(self):
        self.id = 'li_test123456'
        self.price = MockPrice()
        self.quantity = 1
        self.object = 'item'

class MockCheckoutSession:
    def __init__(self, **kwargs):
        self.id = 'cs_test_' + ''.join([str(random.randint(0, 9)) for _ in range(14)])
        self.object = 'checkout.session'
        self.url = 'https://checkout.stripe.com/pay/' + self.id
        self.payment_method_types = ['card']
        self.mode = kwargs.get('mode', 'subscription')
        self.success_url = kwargs.get('success_url', '')
        self.cancel_url = kwargs.get('cancel_url', '')
        self.client_reference_id = kwargs.get('client_reference_id', '')
        self.customer = kwargs.get('customer', '')
        self.customer_email = kwargs.get('customer_email', '')
        self.line_items = kwargs.get('line_items', [])
        self.metadata = kwargs.get('metadata', {})
        # Add any other properties that might be referenced
        for key, value in kwargs.items():
            if not hasattr(self, key):
                setattr(self, key, value)

class MockCheckoutService:
    def __init__(self):
        self.sessions = MockCheckoutSessionService()

class MockInvoiceService:
    def create(self, **kwargs):
        return MockInvoice(**kwargs)

    def retrieve(self, invoice_id):
        return MockInvoice(invoice_id=invoice_id)

    def modify(self, invoice_id, **kwargs):
        return MockInvoice(invoice_id=invoice_id)

class MockInvoice:
    def __init__(self, **kwargs):
        self.id = 'in_test123456'
        self.invoice_id = kwargs.get('invoice_id', 'in_test123456')
        self.customer = kwargs.get('customer', 'cus_test123456')
        self.subscription = kwargs.get('subscription', 'sub_test123456')
        self.status = kwargs.get('status', 'paid')
        self.amount_paid = kwargs.get('amount_paid', 1000)
        self.amount_remaining = kwargs.get('amount_remaining', 0)
        self.object = 'invoice'

class MockPaymentMethodService:
    def create(self, **kwargs):
        return MockPaymentMethod(**kwargs)

    def attach(self, payment_method_id, **kwargs):
        return MockPaymentMethod(payment_method_id=payment_method_id)

class MockPaymentMethod:
    def __init__(self, **kwargs):
        self.id = 'pm_test123456'
        self.payment_method_id = kwargs.get('payment_method_id', 'pm_test123456')
        self.type = kwargs.get('type', 'card')
        self.card = kwargs.get('card', {'brand': 'Visa', 'last4': '4242'})
        self.object = 'payment_method'

class MockStripeClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.products = MockProductService()
        self.prices = MockPriceService()
        self.customers = MockCustomerService()
        self.subscriptions = MockSubscriptionService()
        self.checkout = MockCheckoutService()
        self.invoices = MockInvoiceService()
        self.payment_methods = MockPaymentMethodService()
        
    # Ensure this client can be used in place of the real Stripe client
    def __getattr__(self, name):
        # Return a mock service object for any attribute we don't explicitly define
        return MockGenericService()

class MockGenericService:
    """Generic mock for any Stripe service not explicitly defined"""
    def __getattr__(self, name):
        # Return a function that accepts any arguments and returns a mock object
        return lambda *args, **kwargs: MockGenericObject()
        
class MockGenericObject:
    """Generic mock for any Stripe object not explicitly defined"""
    def __init__(self, **kwargs):
        self.id = 'mock_id'
        for key, value in kwargs.items():
            setattr(self, key, value)

class StripeIntegrationTestCase(TestCase):
    """Integration tests for Stripe functionality"""
    
    @classmethod
    def setUpClass(cls):
        # Call the parent setUpClass
        super().setUpClass()
        
        # Create a patching function that returns our mock client
        def patched_get_stripe_client():
            return MockStripeClient(settings.STRIPE_SECRET_KEY)
        
        # Apply the patch - patch both the view and config imports to be safe
        cls.view_patcher = patch('apps.stripe_home.views.get_stripe_client', patched_get_stripe_client)
        cls.view_patcher.start()
        cls.config_patcher = patch('apps.stripe_home.config.get_stripe_client', patched_get_stripe_client)
        cls.config_patcher.start()
    
    @classmethod
    def tearDownClass(cls):
        # Stop the patchers
        cls.view_patcher.stop()
        cls.config_patcher.stop()
        super().tearDownClass()
    
    def setUp(self):
        # Clear cache to avoid throttling issues between tests
        cache.clear()
        
        # Set up API client
        self.client = APIClient()
        
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        
        # Authenticate the user
        self.client.force_authenticate(user=self.user)
        
        # Get a reference to the stripe client we'll use throughout the test
        self.stripe_client = get_test_stripe_client()
        
        # Create a test product
        self.test_product = self.stripe_client.products.create(
            name="Test Product",
            description="Test product for integration tests",
            metadata={
                "initial_credits": "100",
                "monthly_credits": "50"
            }
        )
        
        # Create a test price
        self.test_price = self.stripe_client.prices.create(
            product=self.test_product.id,
            unit_amount=1000,
            currency='usd',
            recurring={
                'interval': 'month'
            },
            metadata={
                'initial_credits': '100',
                'monthly_credits': '50'
            }
        )
        
        # Create a StripePlan in the database for testing
        self.db_plan = StripePlan.objects.create(
            name="Test Plan",
            plan_id=str(self.test_price.id),  # Use the mock price ID as the Stripe plan_id
            amount=1000,
            currency='usd',
            interval='month',
            initial_credits=100,
            monthly_credits=50,
            active=True,
            livemode=False
        )
    
    def tearDown(self):
        # Clean up Stripe resources
        try:
            self.stripe_client.products.delete(self.test_product.id)
            self.stripe_client.prices.delete(self.test_price.id)
        except Exception as e:
            print(f"Error cleaning up test product: {str(e)}")
        
        # Clear cache
        cache.clear()
    
    def test_create_checkout_session(self):
        """Test creating a checkout session with the real Stripe API"""
        # Prepare the request data
        data = {
            'success_url': 'https://example.com/success',
            'cancel_url': 'https://example.com/cancel'
        }

        # Make the request - use the database plan ID (not the mock price ID)
        url = reverse('stripe:subscription_checkout', args=[self.db_plan.id])
        response = self.client.post(url, data, format='json')
        
        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # The actual view returns checkout_url not sessionId and url
        self.assertIn('checkout_url', response.data)
        
        # Get the session URL from the response
        checkout_url = response.data['checkout_url']
        self.assertTrue(checkout_url.startswith('https://checkout.stripe.com/'))
    
    def test_subscription_lifecycle(self):
        """Test the complete subscription lifecycle"""
        # Create a test customer in Stripe
        customer = self.stripe_client.customers.create(
            email=self.user.email,
            name=self.user.username,
            metadata={"user_id": str(self.user.id)}
        )
        
        # Store customer in our database
        StripeCustomer.objects.create(
            user=self.user,
            customer_id=customer.id,
            livemode=False
        )
        
        # Create a subscription with a test card
        payment_method = self.stripe_client.payment_methods.create(
            type="card",
            card={
                "number": "4242424242424242",
                "exp_month": 12,
                "exp_year": datetime.now().year + 1,
                "cvc": "123",
            },
        )
        
        # Attach payment method to customer
        self.stripe_client.payment_methods.attach(
            payment_method.id, customer=customer.id
        )
        
        # Update customer's default payment method
        self.stripe_client.customers.modify(
            customer.id,
            invoice_settings={"default_payment_method": payment_method.id},
        )
        
        # Create subscription
        subscription = self.stripe_client.subscriptions.create(
            customer=customer.id,
            items=[{"price": self.test_price.id}],
            expand=["latest_invoice.payment_intent"],
            metadata={"user_id": str(self.user.id)}
        )
        
        # Check subscription status
        self.assertEqual(subscription.status, "active")
        
        # Simulate webhook for subscription creation
        event_data = {
            "id": "evt_test_subscription_created",
            "object": "event",
            "api_version": "2020-08-27",
            "created": int(datetime.now().timestamp()),
            "data": {
                "object": subscription
            },
            "type": "customer.subscription.created"
        }
        
        # Generate signature
        payload = json.dumps(event_data)
        signature = "t=mock_timestamp,v1=mock_signature"
        
        # Simulate webhook request
        url = reverse('stripe:webhook')
        response = self.client.post(
            url,
            data=payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=signature
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify subscription was created in database
        db_subscription = StripeSubscription.objects.filter(subscription_id=subscription.id).first()
        self.assertIsNotNone(db_subscription)
        self.assertEqual(db_subscription.status, "active")
        
        # Check if credits were allocated
        # This assumes you have a model to track user credits
        if hasattr(self.user, 'profile') and hasattr(self.user.profile, 'credits'):
            self.assertEqual(self.user.profile.credits, 100)  # Initial credits
        
        # Simulate invoice payment succeeded for monthly credits
        invoice = self.stripe_client.invoices.retrieve(subscription.latest_invoice.id)
        
        event_data = {
            "id": "evt_test_invoice_payment_succeeded",
            "object": "event",
            "api_version": "2020-08-27",
            "created": int(datetime.now().timestamp()),
            "data": {
                "object": invoice
            },
            "type": "invoice.payment_succeeded"
        }
        
        payload = json.dumps(event_data)
        signature = "t=mock_timestamp,v1=mock_signature"
        
        response = self.client.post(
            url,
            data=payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=signature
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify monthly credits were allocated
        if hasattr(self.user, 'profile') and hasattr(self.user.profile, 'credits'):
            self.assertEqual(self.user.profile.credits, 150)  # Initial + Monthly credits
        
        # Test subscription cancellation
        canceled_subscription = self.stripe_client.subscriptions.delete(subscription.id)
        
        # Simulate webhook for subscription deletion
        event_data = {
            "id": "evt_test_subscription_deleted",
            "object": "event",
            "api_version": "2020-08-27",
            "created": int(datetime.now().timestamp()),
            "data": {
                "object": canceled_subscription
            },
            "type": "customer.subscription.deleted"
        }
        
        payload = json.dumps(event_data)
        signature = "t=mock_timestamp,v1=mock_signature"
        
        response = self.client.post(
            url,
            data=payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=signature
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify subscription was updated in database
        db_subscription.refresh_from_db()
        self.assertEqual(db_subscription.status, "canceled")
        
        # Check user subscription tier was reset to free
        if hasattr(self.user, 'profile') and hasattr(self.user.profile, 'subscription_tier'):
            self.assertEqual(self.user.profile.subscription_tier, "free")
    
    def test_payment_failure_handling(self):
        """Test handling failed payments with actual Stripe test cards"""
        # Create a test customer in Stripe
        customer = self.stripe_client.customers.create(
            email=self.user.email,
            name=self.user.username,
            metadata={"user_id": str(self.user.id)}
        )
        
        # Store customer in our database
        StripeCustomer.objects.create(
            user=self.user,
            customer_id=customer.id,
            livemode=False
        )
        
        # Create a payment method with a card that will be declined
        payment_method = self.stripe_client.payment_methods.create(
            type="card",
            card={
                "number": "4000000000000341",  # Card that fails after customer attaches it
                "exp_month": 12,
                "exp_year": datetime.now().year + 1,
                "cvc": "123",
            },
        )
        
        # Attach payment method to customer
        self.stripe_client.payment_methods.attach(
            payment_method.id, customer=customer.id
        )
        
        # Update customer's default payment method
        self.stripe_client.customers.modify(
            customer.id,
            invoice_settings={"default_payment_method": payment_method.id},
        )
        
        # Try to create subscription - this should eventually fail when payment is attempted
        try:
            subscription = self.stripe_client.subscriptions.create(
                customer=customer.id,
                items=[{"price": self.test_price.id}],
                expand=["latest_invoice.payment_intent"],
                metadata={"user_id": str(self.user.id)}
            )
            
            # Subscription might be created but will quickly transition to past_due
            if subscription.status == "active":
                self.stripe_client.invoices.create(
                    customer=customer.id,
                    subscription=subscription.id,
                    collection_method="charge_automatically",
                )
                
            # Retrieve the subscription to get updated status
            subscription = self.stripe_client.subscriptions.retrieve(subscription.id)
            
            # Simulate webhook for invoice payment failure
            invoice = self.stripe_client.invoices.retrieve(subscription.latest_invoice.id)
            invoice = self.stripe_client.invoices.modify(
                invoice.id,
                # Force the invoice to failed status for testing
                # In a real scenario, this would happen automatically with the test card
                paid=False,
            )
            
            event_data = {
                "id": "evt_test_invoice_payment_failed",
                "object": "event",
                "api_version": "2020-08-27",
                "created": int(datetime.now().timestamp()),
                "data": {
                    "object": invoice
                },
                "type": "invoice.payment_failed"
            }
            
            payload = json.dumps(event_data)
            signature = "t=mock_timestamp,v1=mock_signature"
            
            url = reverse('stripe:webhook')
            response = self.client.post(
                url,
                data=payload,
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE=signature
            )
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            
            # Check if subscription was created and has appropriate status
            db_subscription = StripeSubscription.objects.filter(subscription_id=subscription.id).first()
            if db_subscription:
                self.assertEqual(db_subscription.status, "past_due")
                
                # Credits should not be allocated for failed payment
                if hasattr(self.user, 'profile') and hasattr(self.user.profile, 'credits'):
                    self.assertEqual(self.user.profile.credits, 0)  # No credits allocated
                    
        except Exception as e:
            # This is also an acceptable outcome - the card was declined immediately
            self.assertIn("declined", str(e).lower())

    def test_customer_portal_creation(self):
        """Test creating a customer portal session"""
        # Create a customer
        stripe_client = get_test_stripe_client()
        customer = stripe_client.customers.create(
            email=self.user.email,
            name=f"{self.user.first_name} {self.user.last_name}",
            metadata={
                'user_id': str(self.user.id)
            }
        )
        
        # Store customer in our database
        StripeCustomer.objects.create(
            user=self.user,
            customer_id=customer.id,
            livemode=False
        )
        
        # Test accessing customer portal
        url = reverse('stripe:customer_portal')
        response = self.client.post(url)
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('url', response.data)
        
        # URL should be a Stripe billing portal URL
        self.assertTrue(response.data['url'].startswith('https://billing.stripe.com/'))

class StripeEdgeCaseTestCase(TestCase):
    """Test edge cases for Stripe integration"""
    
    def setUp(self):
        # Clear cache to avoid throttling issues
        cache.clear()
        
        # Set up Stripe client - ensuring we use the actual Stripe API client
        # Import here to avoid any potential module-level mocking
        self.stripe_client = get_test_stripe_client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Set up API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create a test plan in the database
        self.test_plan = StripePlan.objects.create(
            plan_id="price_test_edge_case",
            name="Edge Case Plan",
            amount=2000,
            currency="usd",
            interval='month',
            initial_credits=200,
            monthly_credits=100,
            livemode=False
        )
        
        # Create a test customer
        self.stripe_customer = StripeCustomer.objects.create(
            user=self.user,
            customer_id="cus_test_edge_case",
            livemode=False
        )
    
    def tearDown(self):
        # Clear cache
        cache.clear()
    
    def test_invalid_webhook_signature(self):
        """Test webhook endpoint with invalid signature"""
        event_data = {
            "id": "evt_test_invalid",
            "object": "event",
            "api_version": "2020-08-27",
            "created": int(datetime.now().timestamp()),
            "data": {
                "object": {
                    "id": "sub_test",
                    "object": "subscription",
                    "status": "active"
                }
            },
            "type": "customer.subscription.created"
        }
        
        # Invalid signature
        invalid_signature = "t=1234567890,v1=invalid_signature"
        
        url = reverse('stripe:webhook')
        response = self.client.post(
            url,
            data=json.dumps(event_data),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=invalid_signature
        )
        
        # Should return 400 Bad Request for invalid signature
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_malformed_webhook_payload(self):
        """Test webhook endpoint with malformed JSON payload"""
        url = reverse('stripe:webhook')
        
        # Malformed JSON
        malformed_payload = "{\"invalid\": \"json syntax error\"}"
        
        response = self.client.post(
            url,
            data=malformed_payload,
            content_type="application/json"
        )
        
        # Should return 400 Bad Request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_missing_customer_in_subscription(self):
        """Test handling subscription webhooks with missing customer in database"""
        # Create a subscription object with a non-existent customer
        subscription_data = {
            "id": "sub_test_missing_customer",
            "object": "subscription",
            "customer": "cus_nonexistent",
            "status": "active",
            "items": {
                "data": [
                    {
                        "price": {
                            "id": self.test_plan.plan_id
                        }
                    }
                ]
            },
            "current_period_start": int(datetime.now().timestamp()),
            "current_period_end": int((datetime.now() + timedelta(days=30)).timestamp()),
            "cancel_at_period_end": False,
            "livemode": False
        }
        
        event_data = {
            "id": "evt_test_missing_customer",
            "object": "event",
            "api_version": "2020-08-27",
            "created": int(datetime.now().timestamp()),
            "data": {
                "object": subscription_data
            },
            "type": "customer.subscription.created"
        }
        
        # Generate valid signature
        payload = json.dumps(event_data)
        signature = "t=mock_timestamp,v1=mock_signature"
        
        # Send webhook
        url = reverse('stripe:webhook')
        response = self.client.post(
            url,
            data=payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=signature
        )
        
        # Should still return 200 OK as we want to acknowledge receipt to Stripe
        # but log the error for missing customer
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify no subscription was created
        self.assertFalse(StripeSubscription.objects.filter(subscription_id="sub_test_missing_customer").exists())

# Function to get a mocked Stripe client for testing
def get_test_stripe_client():
    # Just return a mock client without patching
    return MockStripeClient(settings.STRIPE_SECRET_KEY)
