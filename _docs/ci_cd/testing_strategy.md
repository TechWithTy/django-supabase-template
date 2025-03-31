# Testing Strategy in CI/CD Pipeline

This document outlines the testing approach used in the django-supabase-template CI/CD pipeline.

## Table of Contents
- [Overview](#overview)
- [Test Types](#test-types)
- [Test Environment](#test-environment)
- [Common Testing Issues](#common-testing-issues)
- [Resolved Testing Challenges](#resolved-testing-challenges)

## Overview

The project implements a comprehensive testing strategy that runs automatically in the CI/CD pipeline. Tests are executed after linting and before building Docker images to ensure code quality and functionality.

## Test Types

### Unit Tests
- Test individual components in isolation
- Fast execution with minimal dependencies
- Focus on business logic and utility functions

### Integration Tests
- Test interactions between components
- Require mock services or actual external dependencies
- Verify proper communication between system parts

### API Tests
- Test REST API endpoints
- Verify request/response patterns
- Check authentication, permissions, and throttling

## Test Environment

The CI/CD pipeline sets up a complete test environment:

### Services
- **PostgreSQL**: Database server (version 15)
  - Configured with test credentials
  - Initialized with test database
  - Health checks ensure availability

- **Redis**: Caching and queuing (version 7)
  - Used for rate limiting and caching
  - Configured with test password

### Supabase Integration
- Mock Supabase services for authentication tests
- Option for real Supabase connection with integration flag
- JWT token validation and user management

### Environment Variables
- Test-specific configuration via environment variables
- Secure handling of credentials using GitHub Secrets
- Fallback values for local development

## Common Testing Issues

### Prometheus Metrics Duplication

When tests load modules multiple times, Prometheus metrics can be registered more than once, causing errors:

```python
ValueError: Duplicated timeseries in CollectorRegistry: {'api_requests_created', 'api_requests_total', 'api_requests'}
```

**Solution**:
```python
# Unregister existing metrics before creating new ones
try:
    for metric in ['api_requests_total', 'api_requests', 'api_requests_created']:
        if metric in REGISTRY._names_to_collectors:
            REGISTRY.unregister(REGISTRY._names_to_collectors[metric])
except Exception:
    pass
```

### pytest_plugins Configuration

Pytest requires that `pytest_plugins` declarations be in the top-level conftest.py file:

```
Defining 'pytest_plugins' in a non-top-level conftest is no longer supported:
It affects the entire test suite instead of just below the conftest as expected.
```

**Solution**:
- Move the `pytest_plugins` declaration to the root conftest.py file
- Remove from app-specific conftest.py files

## Resolved Testing Challenges

### Authentication in Tests

For Django applications with authentication and IP-based throttling:

1. Use direct testing approaches to bypass authentication complexity
2. Override throttling settings in test classes 
3. Generate test tokens and directly set authentication headers
4. Test core functionality directly instead of going through the full Django test client

### Redis Caching Tests

For Redis caching functionality:

1. Clear cache before and after tests to isolate test cases
2. Test cache functions directly rather than through full request/response cycles
3. Generate cache keys in tests the same way application code does
4. Mock external services that would make real API calls

### CI-Specific Test Configuration

Tests in CI environments may behave differently than locally due to:

1. Different environment variables and configurations
2. Resource constraints and timing issues
3. Network access limitations
4. Concurrent test execution

The CI/CD pipeline addresses these challenges with consistent environment setup and appropriate test timeouts.
