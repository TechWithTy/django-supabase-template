from django.db.models import Count, Sum, Avg, F, Q
from django.core.cache import cache
from rest_framework.decorators import api_view
from rest_framework.response import Response
import time
import logging

from apps.caching.utils.redis_cache import cache_result, get_or_set_cache

logger = logging.getLogger(__name__)

# For demonstration purposes - replace with your actual models
try:
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # This is just for the example - in a real app you'd use your actual models
    # For example, if you had Order and OrderItem models
    class MockOrder:
        @classmethod
        def objects(cls):
            return MockQuerySet()
            
    class MockQuerySet:
        def filter(self, *args, **kwargs):
            return self
            
        def annotate(self, *args, **kwargs):
            return self
            
        def values(self, *args):
            return self
            
        def all(self):
            return self
        
        def select_related(self, *args):
            return self
            
        def prefetch_related(self, *args):
            return self
        
        def count(self):
            # Simulate slow query
            time.sleep(1)
            return 100
            
        def first(self):
            time.sleep(1)
            return {"id": 1, "total": 1000, "items": 5}
            
        def __iter__(self):
            # Simulate slow query
            time.sleep(1)
            for i in range(3):
                yield {"id": i, "total": i * 100, "items": i * 2}
                
    Order = MockOrder
    
except ImportError:
    # Fallback for testing
    User = None
    Order = None


@api_view(['GET'])
@cache_result(timeout=60 * 30)  # Cache for 30 minutes
def cached_complex_query(request):
    """
    Example of caching a complex database query with joins and aggregations.
    
    In a real application, this might be a complex report or dashboard query
    that involves multiple tables, joins, and aggregations.
    """
    logger.info("Executing complex database query")
    
    # Example of a complex query that would be expensive to run frequently
    if Order:
        # This is a simplified example - in a real app, this would be a complex query
        # with multiple joins, filters, and aggregations
        results = list(Order.objects
            .filter(Q(status='completed') & Q(total__gt=100))
            .annotate(
                item_count=Count('items'),
                total_value=Sum('total'),
                avg_item_value=Avg('items__price')
            )
            .values('id', 'total_value', 'item_count', 'avg_item_value')
        )
    else:
        # Mock data for demonstration
        time.sleep(2)  # Simulate slow query
        results = [
            {"id": 1, "total_value": 1000, "item_count": 5, "avg_item_value": 200},
            {"id": 2, "total_value": 1500, "item_count": 7, "avg_item_value": 214},
            {"id": 3, "total_value": 800, "item_count": 3, "avg_item_value": 266},
        ]
    
    return Response({
        "results": results,
        "count": len(results),
        "timestamp": time.time()
    })


def get_user_order_stats(user_id):
    """
    Example function that performs a complex query for a specific user.
    
    This demonstrates how to cache results for individual users or entities
    using a function that can be called from multiple views.
    """
    # Create a cache key specific to this user and query
    cache_key = f"user_order_stats:{user_id}"
    
    # Define the expensive query as a function to pass to get_or_set_cache
    def get_stats():
        logger.info(f"Computing order stats for user {user_id}")
        
        if Order:
            # Complex query with joins and aggregations
            result = Order.objects\
                .filter(user_id=user_id)\
                .annotate(
                    order_count=Count('id'),
                    total_spent=Sum('total'),
                    avg_order_value=Avg('total')
                )\
                .values('order_count', 'total_spent', 'avg_order_value')\
                .first()
        else:
            # Mock data
            time.sleep(1.5)  # Simulate slow query
            result = {
                "order_count": 12,
                "total_spent": 2500,
                "avg_order_value": 208.33
            }
            
        return result
    
    # Get from cache or compute and cache for 1 hour
    return get_or_set_cache(cache_key, get_stats, timeout=60*60)


@api_view(['GET'])
def user_order_stats_view(request):
    """
    View that uses the cached user order stats function.
    
    This demonstrates how to use a cached function in a view.
    """
    user_id = request.query_params.get('user_id', '1')
    
    # Get the cached stats or compute them if not cached
    stats = get_user_order_stats(user_id)
    
    return Response({
        "user_id": user_id,
        "stats": stats,
        "timestamp": time.time()
    })
