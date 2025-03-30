from __future__ import annotations

import os

# Import all settings from the main settings file
from .settings import *

# Define that we're in testing mode
TESTING = True

# Override database settings for testing
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
    'local': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
    'supabase': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Set DEBUG to True for testing
DEBUG = True

# Use faster password hasher for testing
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Override REST_FRAMEWORK settings for testing
# Make sure to include the SupabaseJWTAuthentication class
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.authentication.authentication.SupabaseJWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

# Ensure the Supabase JWT middleware is included
# We're referencing MIDDLEWARE from the imported settings
MIDDLEWARE = [m for m in MIDDLEWARE if not m.startswith('django.middleware.csrf')]

# Make sure the Supabase JWT middleware is included
if 'apps.authentication.middleware.SupabaseJWTMiddleware' not in MIDDLEWARE:
    MIDDLEWARE.append('apps.authentication.middleware.SupabaseJWTMiddleware')

# Stripe Configuration for Tests
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', 'sk_test_example_key')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', 'pk_test_example_key')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET_TEST', 'whsec_example_secret')
STRIPE_SECRET_KEY_TEST = os.getenv('STRIPE_SECRET_KEY_TEST', 'sk_test_example_key')

# Force test mode for safety
if 'test' not in STRIPE_SECRET_KEY and not STRIPE_SECRET_KEY.startswith('sk_test_'):
    STRIPE_SECRET_KEY = 'sk_test_example_key'  # Fallback to safe test key

# Disable logging during tests except for test logger
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'test': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        # Disable other loggers
        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# Disable Sentry for tests
SENTRY_DSN = None

# Disable Prometheus for tests
DJANGO_PROMETHEUS_EXPORT_MIGRATIONS = False
