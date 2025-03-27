import os
import logging
import time

# Set Django settings module before importing Django-related modules
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# Load environment variables
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

# Django setup
import django

django.setup()

# Import Django and Redis modules after Django setup
import redis
from django.conf import settings
from django.core.cache import cache

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_redis_connection():
    """
    Test basic Redis connection and operations.
    """
    # Use localhost:6379 since the Redis container exposes this port
    redis_url = "redis://localhost:6379/0"
    logger.info(f"Connecting to Redis at: {redis_url}")

    try:
        # Connect to Redis with explicit parameters to avoid version issues
        r = redis.from_url(redis_url, socket_connect_timeout=5)

        # Test connection with ping
        ping_response = r.ping()
        logger.info(f"Redis ping response: {ping_response}")

        # Test basic operations
        test_key = "django_redis_test"
        test_value = f"Test value at {time.time()}"

        # Set a value
        r.set(test_key, test_value)
        logger.info(f"Set test key: {test_key} = {test_value}")

        # Get the value back
        retrieved_value = r.get(test_key)
        if retrieved_value:
            retrieved_value = retrieved_value.decode("utf-8")
        logger.info(f"Retrieved test key: {test_key} = {retrieved_value}")

        # Verify the value matches
        assert retrieved_value == test_value, "Retrieved value doesn't match set value"

        # Test expiration
        r.setex(f"{test_key}_with_expiry", 5, "This will expire in 5 seconds")
        logger.info("Set key with 5-second expiration")

        # Check it exists
        assert r.exists(f"{test_key}_with_expiry") == 1, "Expiring key doesn't exist"
        logger.info("Verified expiring key exists")

        # Wait for expiration
        logger.info("Waiting for key to expire...")
        time.sleep(6)

        # Verify it's gone
        assert r.exists(f"{test_key}_with_expiry") == 0, "Key should have expired"
        logger.info("Verified key has expired as expected")

        # Test list operations
        list_key = "django_redis_test_list"
        r.delete(list_key)  # Ensure clean state

        # Push items to list
        r.lpush(list_key, "item1", "item2", "item3")
        logger.info(f"Pushed 3 items to list: {list_key}")

        # Get list length
        list_len = r.llen(list_key)
        logger.info(f"List length: {list_len}")
        assert list_len == 3, "List should have 3 items"

        # Get all list items
        items = r.lrange(list_key, 0, -1)
        items = [item.decode("utf-8") for item in items]
        logger.info(f"List items: {items}")

        # Clean up
        r.delete(test_key, list_key)
        logger.info("Cleaned up test keys")

        logger.info("All Redis tests passed successfully!")
        return True

    except redis.RedisError as e:
        logger.error(f"Redis error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False


def fix_django_cache_settings():
    """
    Fix Django cache settings for local testing.
    """
    try:
        # Check if CACHES is defined in settings
        if hasattr(settings, "CACHES") and "default" in settings.CACHES:
            cache_config = settings.CACHES["default"]

            # Log the current configuration
            logger.info(f"Current Django CACHES setting: {cache_config}")

            # Check for HiredisParser issue
            if "OPTIONS" in cache_config and "PARSER_CLASS" in cache_config["OPTIONS"]:
                if (
                    cache_config["OPTIONS"]["PARSER_CLASS"]
                    == "redis.connection.HiredisParser"
                ):
                    logger.info(
                        "Detected HiredisParser configuration which may not be compatible"
                    )

                    # Modify the settings in memory (won't persist)
                    # Remove the PARSER_CLASS option which is causing issues
                    if "PARSER_CLASS" in cache_config["OPTIONS"]:
                        logger.info(
                            "Temporarily removing PARSER_CLASS setting for testing"
                        )
                        del cache_config["OPTIONS"]["PARSER_CLASS"]

            # Update the cache location to use localhost
            if "LOCATION" in cache_config:
                original_location = cache_config["LOCATION"]
                if "redis:6379" in original_location:
                    new_location = original_location.replace(
                        "redis:6379", "localhost:6379"
                    )
                    logger.info(
                        f"Updating cache location from {original_location} to {new_location}"
                    )
                    cache_config["LOCATION"] = new_location

            return True
    except Exception as e:
        logger.error(f"Error fixing Django cache settings: {e}")

    return False


def test_django_cache():
    """
    Test Django's cache framework with Redis backend.
    """
    # Fix Django cache settings first
    fix_django_cache_settings()

    try:
        # Try to import the cache module
        logger.info(f"Django cache backend: {cache.__class__.__name__}")

        logger.info("Testing Django cache framework")

        # Set a cache value
        cache_key = "django_cache_test"
        cache_value = f"Django cache test at {time.time()}"

        try:
            cache.set(cache_key, cache_value, timeout=60)
            logger.info(f"Set cache key: {cache_key} = {cache_value}")

            # Get the cache value
            retrieved_value = cache.get(cache_key)
            logger.info(f"Retrieved cache key: {cache_key} = {retrieved_value}")

            # Verify the value matches
            assert retrieved_value == cache_value, (
                "Retrieved cache value doesn't match set value"
            )

            # Test cache expiration (with a short timeout)
            short_key = "django_cache_short"
            cache.set(short_key, "This will expire quickly", timeout=2)
            logger.info("Set cache key with 2-second timeout")

            # Verify it exists
            assert cache.get(short_key) is not None, (
                "Short-lived cache key should exist"
            )
            logger.info("Verified short-lived cache key exists")

            # Wait for expiration
            logger.info("Waiting for cache key to expire...")
            time.sleep(3)

            # Verify it's gone
            assert cache.get(short_key) is None, "Cache key should have expired"
            logger.info("Verified cache key has expired as expected")

            # Clean up
            cache.delete(cache_key)
            logger.info("Cleaned up test cache keys")

            logger.info("All Django cache tests passed successfully!")
            return True

        except Exception as e:
            logger.error(f"Cache operation error: {e}")
            return False

    except ImportError as e:
        logger.error(f"Cache import error: {e}")
        return False
    except Exception as e:
        logger.error(f"Cache setup error: {e}")
        return False


def check_redis_installation():
    """
    Check Redis client installation and version.
    """
    try:
        logger.info(f"Redis client version: {redis.__version__}")

        # Check if hiredis is installed
        try:
            import hiredis

            logger.info(f"Hiredis version: {hiredis.__version__}")
        except ImportError:
            logger.warning(
                "Hiredis is not installed. For better performance, consider: pip install hiredis"
            )

        return True
    except Exception as e:
        logger.error(f"Error checking Redis installation: {e}")
        return False


if __name__ == "__main__":
    logger.info("Starting Redis tests...")

    # Check Redis installation
    check_redis_installation()

    # Test direct Redis connection
    redis_result = test_redis_connection()

    # Test Django cache framework
    cache_result = test_django_cache()

    if redis_result and cache_result:
        logger.info("\u2705 All Redis tests completed successfully!")
    else:
        logger.error("\u274c Some Redis tests failed!")
        logger.info("\nTo fix Redis connection issues:")
        logger.info(
            "1. Make sure Redis is installed and running locally or Docker containers are running"
        )
        logger.info("2. Check that the Redis URL in .env is correct")
        logger.info(
            "3. For Docker setup, use 'localhost' when testing from host machine"
        )
        logger.info(
            "4. Install required Redis packages: pip install redis django-redis hiredis"
        )
