import os
import sys
import django
import logging

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("supabase_test")

# Import our Supabase client
from apps.supabase.client import supabase
from apps.supabase.init import get_supabase_client
from django.conf import settings


def test_supabase_config():
    """Test that Supabase configuration is properly loaded"""
    logger.info("Testing Supabase configuration...")

    # Check environment variables
    supabase_url = settings.SUPABASE_DB_CONNECTION_STRING
    supabase_anon_key = settings.SUPABASE_ANON_KEY
    supabase_service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY

    logger.info(
        f"SUPABASE_DB_CONNECTION_STRING: {'✓ Set' if supabase_url else '✗ Not set'}"
    )
    logger.info(f"SUPABASE_ANON_KEY: {'✓ Set' if supabase_anon_key else '✗ Not set'}")
    logger.info(
        f"SUPABASE_SERVICE_ROLE_KEY: {'✓ Set' if supabase_service_role_key else '✗ Not set'}"
    )

    # Verify URL format
    if supabase_url and not supabase_url.startswith(("http://", "https://")):
        logger.warning(
            f"SUPABASE_DB_CONNECTION_STRING does not start with http:// or https://: {supabase_url}"
        )

    return all([supabase_url, supabase_anon_key, supabase_service_role_key])


def test_supabase_client_init():
    """Test that the Supabase client can be initialized"""
    logger.info("Testing Supabase client initialization...")

    try:
        # Get the raw client
        raw_client = get_supabase_client()
        logger.info("✓ Successfully initialized raw Supabase client")

        # Get the client from our singleton
        client = supabase.get_raw_client()
        logger.info("✓ Successfully retrieved Supabase client from singleton")

        return True
    except Exception as e:
        logger.error(f"✗ Failed to initialize Supabase client: {str(e)}")
        return False


def test_supabase_auth_service():
    """Test that the Supabase auth service is working"""
    logger.info("Testing Supabase auth service...")

    try:
        auth_service = supabase.get_auth_service()
        logger.info("✓ Successfully retrieved auth service")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to retrieve auth service: {str(e)}")
        return False


def test_supabase_database_service():
    """Test that the Supabase database service is working"""
    logger.info("Testing Supabase database service...")

    try:
        db_service = supabase.get_database_service()
        logger.info("✓ Successfully retrieved database service")

        # Try a simple query (this might fail if the table doesn't exist, which is okay)
        try:
            # Try to fetch data from a public table that should exist in most Supabase projects
            result = db_service.fetch_data(table="_prisma_migrations", limit=1)
            logger.info(f"✓ Successfully executed a test query: {result}")
        except Exception as e:
            logger.warning(f"Could not execute test query: {str(e)}")
            logger.info(
                "This is expected if the table doesn't exist or you don't have access"
            )

        return True
    except Exception as e:
        logger.error(f"✗ Failed to retrieve database service: {str(e)}")
        return False


def run_all_tests():
    """Run all Supabase connection tests"""
    logger.info("=== Starting Supabase Connection Tests ===")

    # Test configuration
    config_ok = test_supabase_config()
    logger.info(f"Configuration test: {'✓ Passed' if config_ok else '✗ Failed'}")

    if not config_ok:
        logger.error("Cannot continue testing without proper configuration")
        return False

    # Test client initialization
    init_ok = test_supabase_client_init()
    logger.info(f"Client initialization test: {'✓ Passed' if init_ok else '✗ Failed'}")

    if not init_ok:
        logger.error("Cannot continue testing without successful client initialization")
        return False

    # Test auth service
    auth_ok = test_supabase_auth_service()
    logger.info(f"Auth service test: {'✓ Passed' if auth_ok else '✗ Failed'}")

    # Test database service
    db_ok = test_supabase_database_service()
    logger.info(f"Database service test: {'✓ Passed' if db_ok else '✗ Failed'}")

    # Overall result
    all_passed = config_ok and init_ok and auth_ok and db_ok
    logger.info("=== Supabase Connection Tests Complete ===")
    logger.info(
        f"Overall result: {'✓ All tests passed' if all_passed else '✗ Some tests failed'}"
    )

    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
