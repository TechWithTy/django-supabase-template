import os
import sys
import django
import logging
from datetime import datetime

# Add the parent directory to the Python path
# This is necessary to find the 'core' module
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.insert(0, backend_dir)

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('supabase_verification')

# Import settings
from django.conf import settings

def verify_supabase_settings():
    """Verify that all required Supabase settings are properly configured"""
    logger.info("Verifying Supabase settings...")
    
    # Check for required settings
    required_settings = [
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY',
        'SUPABASE_SERVICE_ROLE_KEY'
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
        # Try to import the client
        from apps.supabase.init import get_supabase_client
        logger.info("✓ Successfully imported get_supabase_client")
        
        # Try to import the singleton
        from apps.supabase.client import supabase
        logger.info("✓ Successfully imported supabase client singleton")
        
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
        from apps.supabase.init import get_supabase_client
        
        # Try to initialize the client
        client = get_supabase_client()
        logger.info("✓ Successfully initialized Supabase client")
        
        # Check if we can access the client's auth property
        auth = client.auth
        logger.info("✓ Successfully accessed client.auth")
        
        # Check if we can access the client's table method
        table = client.table('non_existent_table')
        logger.info("✓ Successfully accessed client.table method")
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed to initialize Supabase client: {str(e)}")
        return False

def verify_supabase_services():
    """Verify that the Supabase services can be accessed"""
    logger.info("Verifying Supabase services...")
    
    try:
        # Get the client singleton
        from apps.supabase.client import supabase
        
        # Try to access the auth service
        auth_service = supabase.get_auth_service()
        logger.info("✓ Successfully accessed auth service")
        
        # Try to access the database service
        db_service = supabase.get_database_service()
        logger.info("✓ Successfully accessed database service")
        
        # Try to access the storage service
        storage_service = supabase.get_storage_service()
        logger.info("✓ Successfully accessed storage service")
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed to access Supabase services: {str(e)}")
        return False

def run_verification():
    """Run all verification steps"""
    logger.info("=== Starting Supabase Verification ===")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Verify settings
    settings_ok = verify_supabase_settings()
    logger.info(f"Settings verification: {'✓ Passed' if settings_ok else '✗ Failed'}")
    
    # Step 2: Verify client import
    import_ok = verify_supabase_client_import()
    logger.info(f"Client import verification: {'✓ Passed' if import_ok else '✗ Failed'}")
    
    if not import_ok:
        logger.error("Cannot continue verification without successful client import")
        return False
    
    # Step 3: Verify client initialization
    init_ok = verify_supabase_client_initialization()
    logger.info(f"Client initialization verification: {'✓ Passed' if init_ok else '✗ Failed'}")
    
    if not init_ok:
        logger.error("Cannot continue verification without successful client initialization")
        return False
    
    # Step 4: Verify services
    services_ok = verify_supabase_services()
    logger.info(f"Services verification: {'✓ Passed' if services_ok else '✗ Failed'}")
    
    # Overall result
    all_passed = settings_ok and import_ok and init_ok and services_ok
    logger.info("=== Supabase Verification Complete ===")
    logger.info(f"Overall result: {'✓ All verifications passed' if all_passed else '✗ Some verifications failed'}")
    
    return all_passed

if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
