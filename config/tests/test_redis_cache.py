import os
import sys
import logging
import time
import redis
import unittest
from unittest import TestCase, skipIf


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the project root to Python path first
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now add the backend directory to the path
backend_dir = os.path.join(project_root, 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Set up Django settings module before importing Django modules
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.core.settings')

# Now we can import the backend modules
from backend.utils.sensitive import load_environment_files
load_environment_files()  # Load environment variables

# Import cache utilities (excluding ensure_redis_connection which doesn't exist in the module)
from backend.apps.caching.utils.redis_cache import (
    get_or_set_cache, get_cached_result, cache_result, invalidate_cache
)

# Add our own Redis connection helper function
def ensure_redis_connection(max_retries=3, retry_interval=1, password=None, username=None):
    """Helper function to check Redis connectivity"""
    # First, try connecting without a username (standard Redis auth)
    for attempt in range(max_retries):
        try:
            # Get Redis connection details
            redis_password = password or os.getenv('REDIS_PASSWORD')
            
            # Try connecting to Redis directly with just the password (no username)
            # This is the most common Redis authentication method
            r = redis.Redis(
                host='localhost',
                port=int(os.getenv('REDIS_PORT', '6379')),
                db=int(os.getenv('REDIS_DB', '0')),
                password=redis_password,
                socket_timeout=3
            )
            
            # Log connection attempt
            logger.info("Connecting to Redis at localhost:{}/{}".
                        format(os.getenv('REDIS_PORT', '6379'), os.getenv('REDIS_DB', '0')))
            logger.info("Using standard authentication with password")
            
            # Test the connection
            r.ping()  # Will raise exception if connection fails
            
            # Try a basic Redis operation to verify full functionality
            test_key = f"redis_test_{time.time()}"
            r.set(test_key, 'test_value', ex=5)
            test_value = r.get(test_key)
            r.delete(test_key)
            
            if test_value and test_value.decode('utf-8') == 'test_value':
                logger.info("✅ Redis connection successful!")
                return True
            else:
                logger.warning(f"Redis test failed: got {test_value} instead of 'test_value'")
            
        except Exception as e:
            logger.warning(f"Redis connection attempt {attempt+1} failed: {str(e)}")
            
        if attempt < max_retries - 1:
            logger.info(f"Retrying in {retry_interval} second(s)...")
            time.sleep(retry_interval)
    
    logger.error("❌ Could not connect to Redis after multiple attempts")
    return False

# Create a proper mock for Django cache
class MockCache:
    def __init__(self):
        self.store = {}
        
    def get(self, key, default=None):
        return self.store.get(key, default)
        
    def set(self, key, value, timeout=None):
        self.store[key] = value
        
    def delete(self, key):
        if key in self.store:
            del self.store[key]
            return True
        return False
        
    def clear(self):
        self.store.clear()

# Mock Django cache for tests
mock_cache = MockCache()

# Replace the Django cache module with our mock
sys.modules['django.core.cache'] = unittest.mock.MagicMock()
sys.modules['django.core.cache.cache'] = mock_cache

# Default to using the password from the environment file
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')

@skipIf(not ensure_redis_connection(), "Redis is not available for testing")
class RedisCacheTest(TestCase):
    """Test Redis cache operations"""
    
    def setUp(self):
        """Set up a fresh Redis connection for each test"""
        # Create a direct connection to Redis for testing
        self.redis_client = redis.Redis(
            host='localhost',
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '0')),
            password=REDIS_PASSWORD,
            socket_timeout=3
        )
        
    def tearDown(self):
        """Clean up Redis after each test"""
        # Clear all test keys from Redis
        for key in self.redis_client.keys("*"):
            self.redis_client.delete(key)
        logger.info("Redis test database cleared")
        
    def test_simple_cache_operations(self):
        """Test basic Redis operations"""
        # Create a test key
        test_key = "test_simple"
        test_value = "simple_test_value"
        
        # Set a value
        self.redis_client.set(test_key, test_value)
        
        # Get the value back
        result = self.redis_client.get(test_key)
        self.assertEqual(result.decode('utf-8'), test_value)
        
        # Delete the key
        self.redis_client.delete(test_key)
        
        # Verify it's gone
        result = self.redis_client.get(test_key)
        self.assertIsNone(result)

    def test_invalidate_cache(self):
        """Test invalidating specific cache keys"""
        # First, set up a direct test with Redis
        test_key = "test_invalidate"
        test_value = "invalidate_test_value"
        
        # Set a value directly in Redis
        self.redis_client.set(test_key, test_value)
        
        # Check it's there
        self.assertEqual(self.redis_client.get(test_key).decode('utf-8'), test_value)
        
        # Use our function to invalidate
        with unittest.mock.patch('backend.apps.caching.utils.redis_cache.cache.delete',
                       side_effect=lambda k: self.redis_client.delete(k)):
            invalidate_cache(test_key)
        
        # Verify the key is gone
        self.assertIsNone(self.redis_client.get(test_key))

    def test_cache_result_decorator(self):
        """Test the cache_result decorator"""
        # Setup a mock function to decorate
        def mock_func(*args, **kwargs):
            return "decorated_result"
        
        decorated_func = cache_result(timeout=60)(mock_func)

        # Replace django cache with our Redis client
        with unittest.mock.patch('backend.apps.caching.utils.redis_cache.cache.set',
                       side_effect=lambda k, v, timeout: self.redis_client.set(k, v, ex=timeout)):
            with unittest.mock.patch('backend.apps.caching.utils.redis_cache.cache.get',
                           side_effect=lambda k, default=None: self.redis_client.get(k).decode('utf-8') if self.redis_client.get(k) else default):
                # First call - should compute
                result1 = decorated_func("test_arg")
                self.assertEqual(result1, "decorated_result")
                
                # Second call - should use cache
                result2 = decorated_func("test_arg")
                self.assertEqual(result2, "decorated_result")
                
                # Call with different args - should compute new value
                result3 = decorated_func("different_arg")
                self.assertEqual(result3, "decorated_result")

    def test_get_cached_result(self):
        """Test retrieving cached results directly"""
        test_key = "test_get_cached"
        test_value = "cached_test_value"

        # Set a value in Redis
        self.redis_client.set(test_key, test_value)

        # Patch cache.get to use our Redis client
        with unittest.mock.patch('backend.apps.caching.utils.redis_cache.cache.get',
                       side_effect=lambda k, default: self.redis_client.get(k).decode('utf-8') if self.redis_client.get(k) else default):
            # Should return the cached value
            result = get_cached_result(test_key)
            self.assertEqual(result, test_value)
            
            # Key that doesn't exist should return None
            result = get_cached_result("nonexistent_key")
            self.assertIsNone(result)

    def test_get_or_set_cache(self):
        """Test get or set cache functionality"""
        test_key = "test_get_or_set"
        test_value = "get_or_set_value"
        
        # Create a function that returns our test value
        def get_value():
            return test_value
        
        # First call should compute and cache
        with unittest.mock.patch('backend.apps.caching.utils.redis_cache.cache.get',
                    side_effect=lambda k, default=None: self.redis_client.get(k).decode('utf-8') if self.redis_client.get(k) else default):
            with unittest.mock.patch('backend.apps.caching.utils.redis_cache.cache.set',
                        side_effect=lambda k, v, timeout: self.redis_client.set(k, v, ex=timeout)):
                # Should compute and cache
                result1 = get_or_set_cache(test_key, get_value, 60)
                self.assertEqual(result1, test_value)
                
                # Now the value should be in the cache
                self.assertEqual(self.redis_client.get(test_key).decode('utf-8'), test_value)
                
                # Second call should use the cached value
                result2 = get_or_set_cache(test_key, get_value, 60)
                self.assertEqual(result2, test_value)
