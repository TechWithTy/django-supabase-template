import logging
import warnings
import os
import sys
import django
import pytest

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Define pytest plugins at the root level as required by pytest
pytest_plugins = []

# Configure asyncio fixture scope to avoid deprecation warning
pytest_asyncio_default_fixture_loop_scope = "function"

# Suppress specifically the WebSocket task destroyed warnings
class FilterWebSocketWarnings(logging.Filter):
    def filter(self, record):
        # Don't log websocket task destruction warnings
        if 'Task was destroyed but it is pending' in record.getMessage() and 'WebSocketCommonProtocol.close_connection' in record.getMessage():
            return False
        return True

# Configure logging at the start of test session
def pytest_configure(config):
    # Add our websocket filter to the asyncio logger to suppress specific warnings
    asyncio_logger = logging.getLogger('asyncio')
    asyncio_logger.addFilter(FilterWebSocketWarnings())
    
    # Also filter out RuntimeWarnings about coroutines not being awaited
    warnings.filterwarnings("ignore", message="coroutine .* was never awaited")

# Add fixture for properly creating tables in test database
@pytest.fixture(scope='function')
def ensure_test_tables(django_db_setup, django_db_blocker):
    """Ensure all required tables exist in the test database before tests run"""
    with django_db_blocker.unblock():
        from django.core.management import call_command
        # Migrate specific apps that might cause issues
        call_command('migrate', 'credits', verbosity=0)
        call_command('migrate', 'users', verbosity=0)

# Override default databases to include supabase in test isolation
@pytest.fixture(scope='class')
def django_db_setup(request, django_db_setup, django_db_blocker):
    """Custom database setup that adds supabase to available databases"""
    from django.test import override_settings
    
    # Get the existing databases
    from django.conf import settings
    databases = list(settings.DATABASES.keys())
    if 'supabase' not in databases:
        databases.append('supabase')
    
    with override_settings(DATABASE_ROUTERS=[]):
        yield
