# Redis Caching Strategy

## Overview

This document outlines the Redis caching implementation in our Django-Supabase application. The caching strategy is designed to improve performance by reducing database queries and API calls while ensuring data consistency through proper cache invalidation.

## Key Components

### 1. Cache Key Generation

Cache keys are structured to be unique and descriptive, following these patterns:

- **User Authentication**: `auth:user:{hashed_token}`
- **Database Queries**: `db_query:{table}:{hashed_query_params}`
- **Storage Operations**: `storage:list:{bucket_name}:{hashed_path}`

Using hashed values in cache keys prevents sensitive information exposure while maintaining uniqueness.

### 2. Cache Timeouts

Timeouts are configured based on data volatility:

- **User Authentication**: 30 minutes (1800 seconds)
- **Database Queries**: Dynamic based on table (60-300 seconds)
- **Storage Listings**: 5 minutes (300 seconds)

### 3. Cache Invalidation Strategy

Cache invalidation is implemented for write operations to maintain data consistency:

- **Insert Operations**: Invalidate specific cache keys related to the affected table
- **Update Operations**: Broader invalidation of all cache keys for the affected table
- **Delete Operations**: Similar to update, invalidate all cache keys for the affected table
- **File Operations**: Invalidate all cache keys for the affected bucket

## Implementation Details

### Authentication Caching

```python
# Example from auth_view.py
def get_current_user(request):
    # Generate cache key from token
    token_hash = hashlib.md5(token.encode()).hexdigest()
    cache_key = f"auth:user:{token_hash}"
    
    # Try to get from cache first
    cached_user = get_cached_result(cache_key)
    if cached_user:
        return cached_user
        
    # Fetch user and cache result
    user = fetch_user_from_db(token)
    cache.set(cache_key, user, timeout=1800)
    return user
```

### Database Query Caching

```python
# Example from database_view.py
def fetch_data(request):
    # Generate cache key from query parameters
    query_hash = hashlib.md5(str(query_params).encode()).hexdigest()
    cache_key = f"db_query:{table}:{query_hash}"
    
    # Try to get from cache first
    cached_data = get_cached_result(cache_key)
    if cached_data:
        return cached_data
        
    # Fetch data and cache result
    data = fetch_from_database(table, query_params)
    cache.set(cache_key, data, timeout=timeout)
    return data
```

### Cache Invalidation

```python
# Example from database_view.py
def insert_data(request):
    # Insert data into database
    response = db_service.insert_data(table, data)
    
    # Invalidate cache for this table
    cache_pattern = f"db_query:{table}:*"
    keys_to_delete = cache.keys(cache_pattern)
    cache.delete_many(keys_to_delete)
    
    return response
```

## Best Practices

1. **Selective Caching**: Only cache data that is frequently accessed and relatively static
2. **Appropriate Timeouts**: Set cache timeouts based on data volatility
3. **Aggressive Invalidation**: When in doubt, invalidate cache to ensure data consistency
4. **Error Handling**: Always include proper error handling for cache operations
5. **Logging**: Log cache hits/misses for performance monitoring

## Edge Cases and Considerations

### Race Conditions

To prevent race conditions, our implementation:
- Uses atomic operations where possible
- Implements proper error handling
- Uses cache.delete_many() for batch operations

### Cache Stampede

To prevent cache stampede (many concurrent requests trying to rebuild the cache):
- Consider implementing a distributed lock mechanism for high-traffic scenarios
- Use cache.add() instead of cache.set() for initial cache population

### Memory Usage

To manage memory usage:
- Set appropriate cache timeouts
- Use selective caching for important data only
- Monitor Redis memory usage in production

## Monitoring and Maintenance

### Key Metrics to Monitor

- Cache hit/miss ratio
- Redis memory usage
- Cache key count
- Average response time for cached vs. non-cached requests

### Maintenance Tasks

- Periodically review cache timeouts
- Monitor Redis performance
- Consider implementing cache warming for critical data

## Conclusion

Our Redis caching implementation significantly improves application performance while maintaining data consistency through strategic cache invalidation. By following the patterns and practices outlined in this document, developers can effectively utilize and extend the caching system.
