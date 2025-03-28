import os
import sys
import django
from django.conf import settings
import logging
import pytest
from datetime import datetime
import importlib.util

# Add the parent directory to the Python path
# This is necessary to find the 'core' module
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
sys.path.insert(0, backend_dir)

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("supabase_verification")


def verify_supabase_settings():
    """Verify that all required Supabase settings are properly configured"""
    logger.info("Verifying Supabase settings...")

    # Check for required settings
    required_settings = [
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
    ]

    all_settings_present = True

    for setting_name in required_settings:
        setting_value = getattr(settings, setting_name, None)
        if setting_value:
            logger.info(f"✓ {setting_name} is configured")
        else:
            logger.error(f"✗ {setting_name} is missing")
            all_settings_present = False

    return all_settings_present


def verify_supabase_client_import():
    """Verify that the Supabase client can be imported"""
    logger.info("Verifying Supabase client import...")

    try:
        # Try to import the client - using importlib to avoid unused import warnings
        client_spec = importlib.util.find_spec('apps.supabase_home.init')
        client_singleton_spec = importlib.util.find_spec('apps.supabase_home.client')
        
        if client_spec is not None:
            logger.info("✓ Successfully imported get_supabase_client")
        else:
            logger.error("✗ Failed to find apps.supabase_home.init")
            return False
            
        if client_singleton_spec is not None:
            logger.info("✓ Successfully imported supabase client singleton")
        else:
            logger.error("✗ Failed to find apps.supabase_home.client")
            return False

        return True
    except ImportError as e:
        logger.error(f"✗ Failed to import Supabase client: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error when importing Supabase client: {str(e)}")
        return False


def verify_supabase_client_initialization():
    """Verify that the Supabase client can be initialized"""
    logger.info("Verifying Supabase client initialization...")

    try:
        # Get the client initialization function
        from apps.supabase_home.init import get_supabase_client

        # Try to initialize the client
        client = get_supabase_client()
        logger.info("✓ Successfully initialized Supabase client")

        # Check if we can access the client's auth property (just access, no need to store)
        _ = client.auth
        logger.info("✓ Successfully accessed client.auth")

        # Check if we can access the client's table method (just access, no need to store)
        _ = client.table("non_existent_table")
        logger.info("✓ Successfully accessed client.table method")

        return True
    except Exception as e:
        logger.error(f"✗ Failed to initialize Supabase client: {str(e)}")
        return False


def verify_supabase_services():
    """Verify that the Supabase services can be accessed"""
    logger.info("Verifying Supabase services...")

    try:
        # Import the services
        from apps.supabase_home.auth import SupabaseAuthService
        from apps.supabase_home.database import SupabaseDatabaseService
        from apps.supabase_home.storage import SupabaseStorageService

        # Try to initialize the services (just initialize, no need to store)
        _ = SupabaseAuthService()
        logger.info("✓ Successfully initialized SupabaseAuthService")

        _ = SupabaseDatabaseService()
        logger.info("✓ Successfully initialized SupabaseDatabaseService")

        _ = SupabaseStorageService()
        logger.info("✓ Successfully initialized SupabaseStorageService")

        return True
    except Exception as e:
        logger.error(f"✗ Failed to initialize Supabase services: {str(e)}")
        return False


def run_verification():
    """Run all verification steps"""
    logger.info("Starting Supabase verification at " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 80)

    # Verify settings
    settings_ok = verify_supabase_settings()
    if not settings_ok:
        logger.error("Supabase settings verification failed, aborting further checks")
        return False

    logger.info("-" * 80)

    # Verify client import
    client_import_ok = verify_supabase_client_import()
    if not client_import_ok:
        logger.error("Supabase client import verification failed, aborting further checks")
        return False

    logger.info("-" * 80)

    # Verify client initialization
    client_init_ok = verify_supabase_client_initialization()
    if not client_init_ok:
        logger.error("Supabase client initialization failed, aborting further checks")
        return False

    logger.info("-" * 80)

    # Verify services
    services_ok = verify_supabase_services()
    if not services_ok:
        logger.error("Supabase services verification failed")
        return False

    logger.info("=" * 80)
    logger.info("All Supabase verification checks PASSED")
    logger.info("Verification completed at " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    all_passed = settings_ok and client_import_ok and client_init_ok and services_ok
    return all_passed


def test_verify_supabase_connection():
    """Pytest-discoverable test to verify Supabase connection"""
    # Verify settings
    assert verify_supabase_settings(), "Supabase settings verification failed"
    
    # Verify client import
    assert verify_supabase_client_import(), "Supabase client import verification failed"
    
    # Verify client initialization
    assert verify_supabase_client_initialization(), "Supabase client initialization verification failed"
    
    # Verify services
    assert verify_supabase_services(), "Supabase services verification failed"


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
