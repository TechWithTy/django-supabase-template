# Redis Caching Module

## Overview

This module provides a robust Redis caching implementation for the Django-Supabase template. It includes utility functions and decorators for efficient caching operations, following test-driven development practices.

## Features

- Simple cache get/set operations
- Function result caching with automatic key generation
- Cache invalidation utilities
- Decorator-based caching for views and functions
- Configurable cache timeouts

## Quick Start

### Basic Usage

```python
from django.core.cache import cache

# Store a value in the cache (expires in 60 seconds)
cache.set('my_key', 'my_value', 60)

# Retrieve a value from the cache
value = cache.get('my_key')  # Returns None if key doesn't exist
```

### Using the Cache Decorator

```python
from apps.caching.utils.redis_cache import cache_result

@cache_result(timeout=300)  # Cache for 5 minutes
def expensive_function(arg1, arg2):
    # Expensive operation here
    return result
```

### Caching API Views

```python
from rest_framework.decorators import api_view
from rest_framework.response import Response
from apps.caching.utils.redis_cache import cache_result

@api_view(['GET'])
@cache_result(timeout=60 * 5)  # Cache for 5 minutes
def cached_api_view(request):
    # Expensive operation
    result = {'data': 'expensive_result'}
    return Response(result)
```

## Utility Functions

### `get_cached_result`

Retrieve a result from the cache with an optional default value.

### `get_or_set_cache`

Get a value from the cache, or compute and store it if not found.

### `invalidate_cache`

Explicitly invalidate a specific cache key.

### `cache_result` (decorator)

Automatically cache function results based on the function name and arguments.

## Testing

Run the Redis caching tests with:

```bash
python manage.py test tests.test_redis_cache_unit
```

## Documentation

For detailed documentation on the Redis caching implementation, see the [Redis Implementation Guide](_docs/redis/redis_implementation.md).
