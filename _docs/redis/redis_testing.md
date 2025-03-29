# Redis Caching Testing Guide

## Overview

This document outlines the testing strategy for the Redis caching implementation in our Django-Supabase application. The tests ensure that our caching system works correctly, improves performance, and maintains data consistency through proper cache invalidation.

## Test Structure

The testing suite is organized into several modules, each focusing on different aspects of the caching system:

1. **Redis Utility Tests** - Tests for the core caching utility functions
2. **Auth View Caching Tests** - Tests for user authentication caching
3. **Database View Caching Tests** - Tests for database operation caching
4. **Storage Caching Tests** - Tests for storage operation caching
5. **Integration Tests** - End-to-end tests that verify the entire caching system

## Running the Tests

### Prerequisites

- Redis server running locally (default: `redis://127.0.0.1:6379`)
- Django development environment set up

### Running All Tests

To run all Redis caching tests at once, use the provided runner script:

```bash
python backend/apps/caching/tests/run_tests.py
```

Alternatively, you can use Django's test runner directly:

```bash
python manage.py test apps.caching.tests
```

### Running Specific Test Modules

To run specific test modules:

```bash
python manage.py test apps.caching.tests.test_redis_utils
python manage.py test apps.caching.tests.test_auth_caching
python manage.py test apps.caching.tests.test_database_caching
python manage.py test apps.caching.tests.test_storage_caching
python manage.py test apps.caching.tests.test_integration
```

## Test Coverage

### Redis Utility Tests

These tests verify the core caching utility functions:

- `get_cached_result` - Retrieves a cached result or returns a default value
- `get_or_set_cache` - Gets a value from cache or computes and caches it if not found
- `invalidate_cache` - Removes specific cache entries
- `cache_result` decorator - Caches function results based on arguments

### Auth View Caching Tests

These tests verify that user authentication data is properly cached:

- Cache key generation based on JWT token
- Cache hit/miss behavior
- Error handling for invalid tokens

### Database View Caching Tests

These tests verify database operation caching and invalidation:

- `fetch_data` - Caches query results
- `insert_data` - Invalidates relevant cache entries
- `update_data` - Invalidates all cache entries for the affected table
- `delete_data` - Invalidates all cache entries for the affected table

### Storage Caching Tests

These tests verify storage operation caching and invalidation:

- `list_objects` - Caches storage listings
- `upload_file` - Invalidates relevant cache entries
- `delete_file` - Invalidates relevant cache entries

### Integration Tests

These tests verify the entire caching system works together:

- End-to-end request flow with caching
- Cache invalidation across different operations
- Performance improvements with caching

## Mocking Strategy

The tests use Django's testing framework and unittest.mock to isolate components:

- Mock Redis cache for unit tests
- Mock Supabase client for API calls
- Mock database service for database operations

## Performance Testing

The integration tests include performance measurements to verify that caching improves response times:

- First request (cache miss) timing
- Subsequent request (cache hit) timing
- Verification that cached responses are significantly faster

## Test Data Management

Each test follows best practices for test data management:

1. `setUp` - Creates necessary test data and clears the cache
2. `tearDown` - Cleans up test data and clears the cache
3. Isolated test environment using a separate Redis database (DB 1)

## Common Testing Patterns

### Testing Cache Hits

```python
# First request populates cache
with patch('module.cache.get') as mock_cache_get:
    mock_cache_get.return_value = None
    response1 = function_under_test()

# Second request uses cached data
with patch('module.external_service') as mock_service:
    response2 = function_under_test()
    mock_service.assert_not_called()  # Service not called on cache hit
```

### Testing Cache Invalidation

```python
# Set up cache entries
cache.set(key1, data1)
cache.set(key2, data2)

# Perform operation that should invalidate cache
with patch('module.cache.delete_many') as mock_delete:
    response = invalidating_function()
    mock_delete.assert_called_once()

# Verify cache entries are invalidated
assertIsNone(cache.get(key1))
```

## Troubleshooting

### Common Issues

1. **Redis Connection Errors**
   - Ensure Redis server is running
   - Check connection settings in Django settings

2. **Test Failures Due to Stale Cache**
   - Tests should clear cache in setUp/tearDown
   - Manually flush Redis: `redis-cli flushall`

3. **Inconsistent Test Results**
   - Ensure tests are isolated and don't depend on global state
   - Use a separate Redis database for testing

## Conclusion

The Redis caching testing suite provides comprehensive coverage of our caching implementation. By running these tests regularly, we can ensure that our caching system continues to work correctly as the application evolves.
