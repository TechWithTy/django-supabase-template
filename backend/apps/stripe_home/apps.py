from django.apps import AppConfig
import importlib.util


class StripeHomeConfig(AppConfig):
    name = 'apps.stripe_home'
    label = 'stripe_home'  # This controls the DB table name prefix
    verbose_name = 'Stripe Integration'
    
    def ready(self):
        # Import signal handlers or perform other initialization
        # Check if signals module exists before importing
        if importlib.util.find_spec('apps.stripe_home.signals'):
            # Only import if the module exists
            import apps.stripe_home.signals  # noqa
