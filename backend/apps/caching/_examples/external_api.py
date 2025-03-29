import requests
import time
import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from apps.caching.utils.redis_cache import cache_result, get_or_set_cache

logger = logging.getLogger(__name__)


def fetch_external_api_data(endpoint, params=None):
    """
    Fetch data from an external API with caching.
    
    This function demonstrates how to cache external API responses
    to reduce the number of outbound API calls and improve performance.
    """
    # Create a cache key based on the endpoint and parameters
    param_str = "&".join(f"{k}={v}" for k, v in (params or {}).items())
    cache_key = f"external_api:{endpoint}:{param_str}"
    
    # Define the function to fetch data if not cached
    def fetch_data():
        logger.info(f"Fetching data from external API: {endpoint}")
        
        # In a real app, this would be an actual API call
        # For this example, we'll simulate an API call
        try:
            # Simulate API request delay
            time.sleep(2)
            
            # For demonstration, return mock data instead of making a real API call
            # In a real app, this would be something like:
            # response = requests.get(endpoint, params=params)
            # response.raise_for_status()
            # return response.json()
            
            # Mock API response
            return {
                "status": "success",
                "data": {
                    "items": [
                        {"id": 1, "name": "External Item 1"},
                        {"id": 2, "name": "External Item 2"},
                        {"id": 3, "name": "External Item 3"}
                    ],
                    "count": 3,
                    "page": 1,
                    "total_pages": 1
                },
                "timestamp": time.time()
            }
            
        except requests.RequestException as e:
            logger.error(f"External API request failed: {str(e)}")
            # Don't cache errors
            raise
    
    # Cache the API response for 30 minutes
    # Adjust the timeout based on how frequently the external data changes
    return get_or_set_cache(cache_key, fetch_data, timeout=60*30)


@api_view(['GET'])
def weather_api_example(request):
    """
    Example view that fetches and caches weather data from an external API.
    
    This demonstrates caching for an external API that might have rate limits
    or slow response times.
    """
    city = request.query_params.get('city', 'New York')
    
    try:
        # In a real app, this would be an actual weather API endpoint
        endpoint = "https://api.example.com/weather"
        params = {"city": city, "units": "metric"}
        
        # Fetch weather data with caching
        weather_data = fetch_external_api_data(endpoint, params)
        
        return Response({
            "city": city,
            "weather": weather_data,
            "cached": True,  # This indicates the response might be cached
            "timestamp": time.time()
        })
        
    except Exception as e:
        return Response({
            "error": str(e),
            "message": "Failed to fetch weather data"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@cache_result(timeout=60*60)  # Cache for 1 hour
def stock_price_example(request):
    """
    Example view that fetches and caches stock price data.
    
    This demonstrates using the cache_result decorator for an external API call.
    """
    symbol = request.query_params.get('symbol', 'AAPL')
    
    # Log that we're executing the API call
    logger.info(f"Fetching stock data for {symbol}")
    
    # Simulate an external API call
    time.sleep(1.5)
    
    # Mock stock data
    stock_data = {
        "symbol": symbol,
        "price": 150.25,
        "change": 2.5,
        "change_percent": 1.7,
        "volume": 32500000,
        "market_cap": 2500000000000,
        "timestamp": time.time()
    }
    
    return Response(stock_data)
