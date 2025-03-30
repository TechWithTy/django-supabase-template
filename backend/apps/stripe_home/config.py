from django.conf import settings
from stripe import StripeClient

class StripeConfig:
    """Configuration utilities for Stripe integration"""
    
    @classmethod
    def is_test_mode(cls):
        """Check if Stripe is in test mode"""
        return settings.STRIPE_SECRET_KEY.startswith('sk_test_')
    
    @classmethod
    def get_test_card_numbers(cls):
        """Return test card numbers for different scenarios"""
        return {
            'success': '4242424242424242',
            'requires_auth': '4000002500003155',
            'declined': '4000000000000002',
            'insufficient_funds': '4000000000009995',
            'processing_error': '4000000000000119',
        }
    
    @classmethod
    def get_test_dashboard_url(cls, object_id, object_type):
        """Generate Stripe dashboard URL for test objects"""
        base_url = 'https://dashboard.stripe.com/test/'
        paths = {
            'customer': f'customers/{object_id}',
            'subscription': f'subscriptions/{object_id}',
            'payment': f'payments/{object_id}',
            'invoice': f'invoices/{object_id}',
        }
        return base_url + paths.get(object_type, '')


def get_stripe_client():
    """Get a configured Stripe client instance"""
    return StripeClient(settings.STRIPE_SECRET_KEY)
