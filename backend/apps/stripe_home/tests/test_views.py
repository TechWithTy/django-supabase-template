import json
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.cache import cache

from rest_framework.test import APIClient
from rest_framework import status

import stripe

from ..models import StripeCustomer, StripePlan, StripeSubscription
from ..config import get_stripe_client

User = get_user_model()

# Make sure we're using test API keys
assert 'test' in settings.STRIPE_SECRET_KEY or settings.STRIPE_SECRET_KEY.startswith('sk_test_')


@override_settings(
    # Disable throttling for tests
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {
            'user': None,
            'user_ip': None,
            'anon': None,
        }
    }
)
class CheckoutSessionViewTest(TestCase):
    """Test creating checkout sessions with real Stripe API in test mode"""
    
    def setUp(self):
        # Clear cache to avoid throttling issues
        cache.clear()
        
        # Set up Stripe client
        self.stripe_client = get_stripe_client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create API client and authenticate
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create a test product and price in Stripe
        self.test_product = self.stripe_client.products.create(
            name="Test Plan",
            description="Test plan for view tests",
            metadata={
                "initial_credits": "100",
                "monthly_credits": "50"
            }
        )
        
        self.test_price = self.stripe_client.prices.create(
            product=self.test_product.id,
            unit_amount=1500,  # $15.00
            currency="usd",
            recurring={"interval": "month"}
        )
        
        # Create a test plan in the database
        self.test_plan = StripePlan.objects.create(
            plan_id=self.test_price.id,
            name=self.test_product.name,
            amount=self.test_price.unit_amount,
            currency=self.test_price.currency,
            interval='month',
            initial_credits=100,
            monthly_credits=50,
            livemode=False
        )
        
        # URL for checkout session endpoint
        self.url = reverse('stripe:checkout-session')
    
    def tearDown(self):
        # Clean up Stripe resources
        try:
            self.stripe_client.products.delete(self.test_product.id)
        except Exception as e:
            print(f"Error cleaning up test product: {str(e)}")
        
        # Clear cache
        cache.clear()
    
    def test_create_checkout_session_success(self):
        """Test successful creation of a checkout session"""
        # Request data
        data = {
            'plan_id': self.test_price.id,
            'success_url': 'https://example.com/success',
            'cancel_url': 'https://example.com/cancel'
        }
        
        # Make request
        response = self.client.post(self.url, data, format='json')
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('sessionId', response.data)
        self.assertIn('url', response.data)
        
        # Verify the session exists in Stripe
        session_id = response.data['sessionId']
        session = self.stripe_client.checkout.sessions.retrieve(session_id)
        
        self.assertEqual(session.payment_method_types[0], 'card')
        self.assertEqual(session.mode, 'subscription')
        self.assertEqual(session.client_reference_id, str(self.user.id))
    
    def test_create_checkout_session_invalid_plan(self):
        """Test checkout session creation with invalid plan ID"""
        # Request with non-existent plan ID
        data = {
            'plan_id': 'price_invalid_id',
            'success_url': 'https://example.com/success',
            'cancel_url': 'https://example.com/cancel'
        }
        
        # Make request
        response = self.client.post(self.url, data, format='json')
        
        # Should return an error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_create_checkout_session_missing_fields(self):
        """Test checkout session creation with missing required fields"""
        # Missing success_url
        data = {
            'plan_id': self.test_price.id,
            'cancel_url': 'https://example.com/cancel'
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Missing cancel_url
        data = {
            'plan_id': self.test_price.id,
            'success_url': 'https://example.com/success'
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Missing plan_id
        data = {
            'success_url': 'https://example.com/success',
            'cancel_url': 'https://example.com/cancel'
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_unauthenticated_request(self):
        """Test checkout session creation without authentication"""
        # Create an unauthenticated client
        client = APIClient()
        
        data = {
            'plan_id': self.test_price.id,
            'success_url': 'https://example.com/success',
            'cancel_url': 'https://example.com/cancel'
        }
        
        # Make unauthenticated request
        response = client.post(self.url, data, format='json')
        
        # Should require authentication
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class StripeWebhookViewTest(TestCase):
    """Test handling webhook events from Stripe"""
    
    def setUp(self):
        # Set up Stripe client
        self.stripe_client = get_stripe_client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='webhookuser',
            email='webhook@example.com',
            password='testpassword'
        )
        
        # Create Stripe customer
        self.stripe_customer = StripeCustomer.objects.create(
            user=self.user,
            customer_id='cus_test_webhook',
            livemode=False
        )
        
        # Create a test plan
        self.test_plan = StripePlan.objects.create(
            plan_id='price_test_webhook',
            name='Webhook Test Plan',
            amount=2000,
            currency='usd',
            interval='month',
            initial_credits=100,
            monthly_credits=50,
            livemode=False
        )
        
        # URL for webhook endpoint
        self.url = reverse('stripe:webhook')
    
    def test_webhook_without_signature(self):
        """Test webhook endpoint called without Stripe signature"""
        # Create dummy event data
        event_data = {
            "id": "evt_test",
            "object": "event",
            "type": "customer.subscription.created"
        }
        
        # Make request without signature
        response = self.client.post(
            self.url,
            data=json.dumps(event_data),
            content_type="application/json"
        )
        
        # Should return 400 Bad Request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_webhook_with_known_event_type(self):
        """Test webhook with a known event type that we handle"""
        # Create a valid subscription object similar to what Stripe would send
        subscription_data = {
            "id": "sub_test_webhook",
            "object": "subscription",
            "customer": self.stripe_customer.customer_id,
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
            "current_period_start": 1677845000,  # Example timestamp
            "current_period_end": 1680523400,    # Example timestamp
            "cancel_at_period_end": False,
            "livemode": False
        }
        
        # Create the event with known type
        event_data = {
            "id": "evt_test_webhook",
            "object": "event",
            "api_version": "2020-08-27",
            "created": 1677845000,
            "data": {
                "object": subscription_data
            },
            "type": "customer.subscription.created"
        }
        
        # Generate a valid signature
        timestamp = 1677845000
        payload = json.dumps(event_data)
        signature = stripe.webhook.WebhookSignature.generate_signature(
            timestamp,
            payload.encode('utf-8'),
            settings.STRIPE_WEBHOOK_SECRET,
        )
        
        # Send webhook with signature
        response = self.client.post(
            self.url,
            data=payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=f"t={timestamp},v1={signature}"
        )
        
        # Should return 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify subscription was created in database
        self.assertTrue(StripeSubscription.objects.filter(subscription_id="sub_test_webhook").exists())
    
    def test_webhook_with_unknown_event_type(self):
        """Test webhook with unknown event type"""
        # Create an event with an unknown type
        event_data = {
            "id": "evt_test_unknown",
            "object": "event",
            "api_version": "2020-08-27",
            "created": 1677845000,
            "data": {
                "object": {}
            },
            "type": "unknown.event.type"
        }
        
        # Generate a valid signature
        timestamp = 1677845000
        payload = json.dumps(event_data)
        signature = stripe.webhook.WebhookSignature.generate_signature(
            timestamp,
            payload.encode('utf-8'),
            settings.STRIPE_WEBHOOK_SECRET,
        )
        
        # Send webhook with signature
        response = self.client.post(
            self.url,
            data=payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=f"t={timestamp},v1={signature}"
        )
        
        # Should still return 200 OK (acknowledge receipt to Stripe)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
