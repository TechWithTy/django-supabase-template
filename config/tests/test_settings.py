"""Custom settings for tests that need to run without certain models."""

# Import existing settings
from core.settings import *

# Remove authentication app and stripe_home app from INSTALLED_APPS
INSTALLED_APPS = [app for app in INSTALLED_APPS if app not in (
    'backend.apps.authentication',
    'backend.apps.stripe_home',
)]

# Disable migrations
MIGRATION_MODULES = {app.split('.')[-1]: None for app in INSTALLED_APPS}

# Use in-memory SQLite database instead of PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Set an alternative User model if needed
# AUTH_USER_MODEL = 'auth.User'
