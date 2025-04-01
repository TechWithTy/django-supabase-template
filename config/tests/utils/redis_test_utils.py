import redis
import logging
import time
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

def ensure_redis_connection(max_retries=3, retry_interval=2):
    """
    Ensures a Redis connection is available before running tests.
    Returns True if connection is successful, False otherwise.
    
    Args:
        max_retries: Maximum number of retry attempts
        retry_interval: Time interval in seconds between retries
    """
    retries = 0
    
    while retries < max_retries:
        try:
            # Get Redis URL from settings
            redis_url = getattr(settings, 'REDIS_URL', None)
            
            if not redis_url and hasattr(settings, 'CACHES'):
                redis_url = settings.CACHES.get('default', {}).get('LOCATION', '')
                
            if not redis_url:
                redis_url = "redis://localhost:6379/1"  # Default fallback
                
            logger.info(f"Attempting to connect to Redis at {redis_url}")
            
            # Clean up the redis URL if it has the redis:// prefix
            if redis_url.startswith('redis://'):
                redis_url = redis_url[len('redis://'):]  
            
            # Parse host and port from URL
            if '/' in redis_url:
                host_port, db = redis_url.rsplit('/', 1)
            else:
                host_port, db = redis_url, '0'
                
            if ':' in host_port:
                host, port = host_port.split(':')
            else:
                host, port = host_port, '6379'
                
            # Try to connect directly with redis-py
            r = redis.Redis(host=host, port=int(port), db=int(db), socket_timeout=5)
            r.ping()  # This will raise an exception if the connection fails
            
            # Also try a simple Django cache operation
            cache.set('redis_test_key', 'test_value', 10)
            test_value = cache.get('redis_test_key')
            
            if test_value != 'test_value':
                raise Exception(f"Cache test failed: got {test_value} instead of 'test_value'")
                
            logger.info("✅ Redis connection successful!")
            return True
            
        except Exception as e:
            logger.warning(f"Redis connection attempt {retries+1} failed: {str(e)}")
            retries += 1
            
            if retries < max_retries:
                logger.info(f"Retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)
    
    logger.error(f"❌ Could not connect to Redis after {max_retries} attempts")
    return False
