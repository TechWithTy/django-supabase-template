import os
import sys
import django
import pytest
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Set test database settings to avoid actual database connections
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'

# Initialize Django
django.setup()

# Create a pytest.ini file to disable database access
pytest_plugins = []

@pytest.fixture
def supabase_client():
    """Fixture to provide a Supabase client for tests"""
    from apps.supabase.init import get_supabase_client
    return get_supabase_client()

@pytest.fixture
def supabase_service():
    """Fixture to provide a Supabase service for tests"""
    from apps.supabase.service import SupabaseService
    return SupabaseService()
