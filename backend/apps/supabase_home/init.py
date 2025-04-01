from django.conf import settings
import logging
import sys
from backend.utils.sensitive import load_environment_files
import os

# Load environment variables
load_environment_files()

# Force Python to look for the supabase package in site-packages first
# This prevents our local 'supabase' module from shadowing the installed library
for path in sys.path:
    if "site-packages" in path:
        sys.path.insert(0, path)
        break

# Now import from the actual supabase-py library

try:
        # Try alternative import path (depending on how the package was installed)
    from supabase import create_client, Client
except ImportError:
    raise ImportError(
        "Could not import 'create_client' from either 'supabase_py' or 'supabase'. "
        "Please ensure the supabase-py package is installed using: "
        "pip install supabase"
    )

logger = logging.getLogger(" apps.supabase_home")

# Global variable to hold the Supabase client instance
_supabase_client = None


def initialize_supabase() -> Client:
    """
    Initialize the Supabase client using settings from Django configuration.

    This function checks for required environment variables and creates a
    Supabase client instance using the official supabase-py library.

    Returns:
        Client: An initialized Supabase client instance

    Raises:
        ValueError: If required environment variables are missing
    """
    global _supabase_client

    # If client is already initialized, return it
    if _supabase_client is not None:
        return _supabase_client

    # Check for required environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")

    print(f"Supabase URL: {supabase_url}")  # Added print statement to show the URL

    if not supabase_url:
        error_msg = "SUPABASE_URL is not set in environment variables"
        logger.error(error_msg)
        raise ValueError(error_msg)

    if not supabase_key:
        error_msg = "SUPABASE_ANON_KEY is not set in environment variables"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Log initialization (without sensitive info)
    logger.info(f"Initializing Supabase client with URL: {supabase_url}")

    try:
        # Create the Supabase client
        _supabase_client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized successfully")
        return _supabase_client
    except Exception as e:
        logger.exception(f"Failed to initialize Supabase client: {str(e)}")
        raise


def get_supabase_client() -> Client:
    """
    Get the Supabase client instance, initializing it if necessary.

    This is the recommended way to access the Supabase client throughout the application.

    Returns:
        Client: The Supabase client instance

    Raises:
        ValueError: If required environment variables are missing
    """
    global _supabase_client

    if _supabase_client is None:
        return initialize_supabase()

    return _supabase_client
