from rest_framework.decorators import api_view
from rest_framework.response import Response
import time
import logging

from apps.caching.utils.redis_cache import cache_result

logger = logging.getLogger(__name__)


@api_view(['GET'])
@cache_result(timeout=60 * 15)  # Cache for 15 minutes
def expensive_api_example(request):
    """
    Example of caching an expensive API route.
    
    This demonstrates how to cache the entire response of an API endpoint
    that might be computationally expensive or time-consuming.
    """
    # Log that we're executing the expensive operation
    logger.info("Executing expensive API operation")
    
    # Simulate an expensive operation
    time.sleep(2)  # Simulate 2-second delay
    
    # Generate a complex response
    result = {
        "data": [
            {"id": 1, "name": "Item 1", "value": 100},
            {"id": 2, "name": "Item 2", "value": 200},
            {"id": 3, "name": "Item 3", "value": 300},
        ],
        "metadata": {
            "count": 3,
            "timestamp": time.time(),
            "source": "expensive_api"
        }
    }
    
    return Response(result)
