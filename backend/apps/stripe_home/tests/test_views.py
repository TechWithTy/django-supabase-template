import json
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.cache import cache
import os
import stripe
import hmac
import hashlib
import time
from django.utils import timezone
import datetime

from rest_framework.test import APIClient
from rest_framework import status

from apps.stripe_home.config import get_stripe_client
from apps.stripe_home.models import StripeCustomer, StripePlan, StripeSubscription

User = get_user_model()

# Make sure we're using test API keys
assert "test" in settings.STRIPE_SECRET_KEY or settings.STRIPE_SECRET_KEY.startswith(
    "sk_test_"
)
STRIPE_API_KEY = (
    settings.STRIPE_SECRET_KEY_TEST
    if getattr(settings, "TESTING", False)
    else settings.STRIPE_SECRET_KEY
)


@override_settings(
    # Disable throttling for tests
    REST_FRAMEWORK={
        "DEFAULT_THROTTLE_CLASSES": [],
        "DEFAULT_THROTTLE_RATES": {
            "user": None,
            "user_ip": None,
            "anon": None,
        },
    }
)
class CheckoutSessionViewTest(TestCase):
    """Test creating checkout sessions with real Stripe API in test mode"""

    def setUp(self):
        # Set test mode
        from django.conf import settings

        settings.TEST_MODE = True

        # Clear cache to avoid throttling issues
        cache.clear()

        # Set up Stripe client and configure API key for direct stripe module calls
        self.stripe_client = get_stripe_client()
        stripe.api_key = STRIPE_API_KEY

        # Create test user
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword"
        )

        # Create API client and authenticate
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create a test product and price in Stripe
        self.test_product = stripe.Product.create(
            name="Test Plan",
            description="Test plan for view tests",
            metadata={"initial_credits": "100", "monthly_credits": "50"},
        )

        self.test_price = stripe.Price.create(
            product=self.test_product.id,
            unit_amount=1500,  # $15.00
            currency="usd",
            recurring={"interval": "month"},
        )

        # Create a test plan in the database
        self.test_plan = StripePlan.objects.create(
            plan_id=self.test_price.id,
            name=self.test_product.name,
            amount=self.test_price.unit_amount,
            currency=self.test_price.currency,
            interval="month",
            initial_credits=100,
            monthly_credits=50,
            livemode=False,
        )

        # Create a customer in Stripe
        self.test_customer = stripe.Customer.create(
            email=self.user.email,
            name=self.user.username,
            metadata={"user_id": str(self.user.id)},
        )

        # Save customer in database
        self.customer = StripeCustomer.objects.create(
            user=self.user, customer_id=self.test_customer.id
        )

        # URL for programmable checkout endpoint
        self.url = reverse("stripe:programmable_checkout")

    def tearDown(self):
        # Clean up Stripe resources
        try:
            # Can't delete products with prices, need to update instead
            stripe.Product.modify(self.test_product.id, active=False)
        except Exception as e:
            print(f"Error cleaning up test product: {str(e)}")

        # Clean up database objects
        self.test_plan.delete()
        self.customer.delete()

    def test_create_checkout_session_success(self):
        """Test successful creation of a checkout session"""
        # Request data
        data = {
            "plan_id": self.test_price.id,
            "success_url": "https://example.com/success?session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": "https://example.com/cancel",
        }

        # Make request
        response = self.client.post(self.url, data, format="json")

        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("sessionId", response.data)
        self.assertIn("url", response.data)

        # Verify the session exists in Stripe
        session_id = response.data["sessionId"]
        session = stripe.checkout.Session.retrieve(session_id)

        self.assertEqual(session.payment_method_types[0], "card")
        self.assertEqual(session.mode, "subscription")
        self.assertEqual(session.client_reference_id, str(self.user.id))


class StripeWebhookViewTest(TestCase):
    """Test handling webhook events from Stripe"""

    def setUp(self):
        # Set test mode
        from django.conf import settings

        settings.TEST_MODE = True

        # Set up Stripe client and configure API key for direct stripe module calls
        self.stripe_client = get_stripe_client()
        stripe.api_key = STRIPE_API_KEY

        # Create test user
        self.user = User.objects.create_user(
            username="webhookuser", email="webhook@example.com", password="testpassword"
        )

        # Create Stripe customer
        self.stripe_customer = StripeCustomer.objects.create(
            user=self.user, customer_id="cus_test_webhook", livemode=False
        )

        # Create a test plan
        self.test_plan = StripePlan.objects.create(
            plan_id="price_test_webhook",
            name="Webhook Test Plan",
            amount=2000,
            currency="usd",
            interval="month",
            initial_credits=100,
            monthly_credits=50,
            livemode=False,
        )

        # URL for webhook endpoint
        self.url = reverse("stripe:webhook")

    def test_webhook_without_signature(self):
        """Test webhook endpoint called without Stripe signature"""
        # Create dummy event data
        event_data = {
            "id": "evt_test",
            "object": "event",
            "type": "customer.subscription.created",
        }

        # Make request without signature
        response = self.client.post(
            self.url, data=json.dumps(event_data), content_type="application/json"
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
            "items": {"data": [{"price": {"id": self.test_plan.plan_id}}]},
            "current_period_start": int(time.time()) - 86400,  # Yesterday
            "current_period_end": int(time.time()) + 86400,  # Tomorrow
            "cancel_at_period_end": False,
            "livemode": False,
        }

        # Create the event with known type
        event_data = {
            "id": "evt_test_webhook",
            "object": "event",
            "api_version": "2020-08-27",
            "created": int(time.time()),
            "data": {"object": subscription_data},
            "type": "customer.subscription.created",
        }

        # Mock stripe.Webhook.construct_event to bypass signature verification
        from unittest.mock import patch, MagicMock

        # Create a proper mock event structure that matches what Stripe sends
        # and what our handler expects
        mock_event = MagicMock()
        mock_event.type = "customer.subscription.created"
        mock_event.id = "evt_test_webhook"

        # Set up the data.object structure to match a Stripe subscription
        mock_subscription = MagicMock()
        mock_subscription.id = "sub_test_webhook"
        mock_subscription.customer = self.stripe_customer.customer_id
        mock_subscription.status = "active"
        mock_subscription.current_period_start = (
            int(time.time()) - 86400
        )  # Unix timestamp for yesterday
        mock_subscription.current_period_end = (
            int(time.time()) + 86400
        )  # Unix timestamp for tomorrow
        mock_subscription.cancel_at_period_end = False
        mock_subscription.livemode = False

        # Create the items.data[0].price.id structure
        mock_price = MagicMock()
        mock_price.id = self.test_plan.plan_id

        mock_item = MagicMock()
        mock_item.price = mock_price

        mock_items = MagicMock()
        mock_items.data = [mock_item]

        mock_subscription.items = mock_items

        # Attach the mock subscription to the event
        mock_event.data.object = mock_subscription

        # Payload with proper format for the webhook
        payload = json.dumps(event_data)

        # Use patch to mock the Stripe webhook construct_event method
        with patch("stripe.Webhook.construct_event", return_value=mock_event):
            # Send webhook with a dummy signature
            response = self.client.post(
                self.url,
                data=payload,
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="t=123456,v1=dummy_signature",
            )

            # Should return 200 OK
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # Verify subscription was created in database
            self.assertTrue(
                StripeSubscription.objects.filter(
                    subscription_id="sub_test_webhook"
                ).exists()
            )
