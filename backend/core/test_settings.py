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
# Use a simpler authentication class that doesn't validate tokens
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

# Disable middleware that might slow down tests
# We're referencing MIDDLEWARE from the imported settings
MIDDLEWARE = [m for m in MIDDLEWARE if not m.startswith('django.middleware.csrf')]

# Disable logging during tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['null'],
            'propagate': False,
        },
    },
}

# Disable Sentry for tests
SENTRY_DSN = None

# Disable Prometheus for tests
DJANGO_PROMETHEUS_EXPORT_MIGRATIONS = False
