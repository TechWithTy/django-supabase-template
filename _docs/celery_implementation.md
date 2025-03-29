# Celery Implementation Guide

## Overview

This document provides a comprehensive guide to the Celery implementation in the Django Supabase Template project. Celery is used for handling background tasks, periodic scheduling, and asynchronous processing of credit-related operations.

## Architecture

The Celery implementation follows a test-driven approach with the following components:

1. **Celery Worker**: Processes asynchronous tasks in the background
2. **Celery Beat**: Schedules periodic tasks at configured intervals
3. **Redis**: Used as both the message broker and result backend
4. **Django Integration**: Celery is integrated with Django for seamless operation

## Configuration

The Celery configuration is defined in `backend/core/celery.py` and includes:

- Task auto-discovery for finding tasks in Django apps
- Redis connection settings from environment variables
- Task serialization and execution settings

Additional settings in `backend/core/settings.py` include the Beat schedule:

```python
CELERY_BEAT_SCHEDULE = {
    'cleanup-expired-credit-holds': {
        'task': 'apps.credits.tasks.cleanup_expired_credit_holds',
        'schedule': crontab(minute='0', hour='*/3'),  # Run every 3 hours
    },
    'periodic-credit-allocation': {
        'task': 'apps.credits.tasks.periodic_credit_allocation',
        'schedule': crontab(minute='0', hour='0', day_of_month='1'),  # Run on 1st of every month
    },
    'process-pending-credit-transactions': {
        'task': 'apps.credits.tasks.process_pending_transactions',
        'schedule': crontab(minute='*/15'),  # Run every 15 minutes
    },
    'sync-credit-usage-with-supabase': {
        'task': 'apps.credits.tasks.sync_credit_usage_with_supabase',
        'schedule': crontab(minute='*/10'),  # Run every 10 minutes
    },
}
```

## Implemented Tasks

The following Celery tasks have been implemented in `apps/credits/tasks.py`:

### 1. Cleanup Expired Credit Holds

```python
@shared_task
def cleanup_expired_credit_holds():
    # Finds and releases all expired credit holds
    # Returns credits to users
```

This task runs every 3 hours to find and release credit holds that have expired, ensuring that temporarily held credits don't remain locked indefinitely.

### 2. Periodic Credit Allocation

```python
@shared_task
def periodic_credit_allocation():
    # Allocates monthly credits to users based on subscription level
    # Creates credit transactions and updates user balances
```

This task runs on the 1st of every month to allocate free credits to users based on their subscription level (standard or premium).

### 3. Process Pending Transactions

```python
@shared_task
def process_pending_transactions():
    # Handles transactions that have been in pending state for too long
    # Finalizes or cancels transactions based on their type
```

This task runs every 15 minutes to process transactions that have been in a pending state for too long (e.g., > 24 hours). It either commits the transaction or reverts it based on the transaction type.

### 4. Sync Credit Usage with Supabase

```python
@shared_task
def sync_credit_usage_with_supabase():
    # Syncs credit usage data with Supabase for analytics
    # Marks transactions as synced after successful synchronization
```

This task runs every 10 minutes to ensure that credit usage data is properly synchronized with Supabase for real-time analytics and reporting.

## Database Models

The credit system uses the following models:

1. **CreditTransaction**: Records all credit movements (additions, deductions, holds)
   - Added `synced_to_supabase` flag to track synchronization status
   - Added `status` field to track transaction state (COMPLETED, PENDING, FAILED)
   - Added `notes` field for additional context

2. **CreditHold**: Tracks temporary holds on credits for long-running operations

3. **CreditUsageRate**: Defines credit costs for different operations

## Testing

The Celery tasks are tested using pytest with proper isolation and mocking:

```python
# Example test for sync_credit_usage_with_supabase task
@patch('apps.supabase_home.init.get_supabase_client')
def test_sync_credit_usage_with_supabase(mock_get_client, setup_mocks):
    # Test implementation
```

Test files:
- `apps/credits/tests/test_celery_tasks.py`: Tests all credit-related Celery tasks

Run tests with:
```bash
pytest apps/credits/tests/test_celery_tasks.py -v
```

## Development Setup

1. **Start Redis**: Ensure Redis is running for local development
   ```bash
   docker run -d -p 6379:6379 redis:alpine
   ```

2. **Start Celery Worker**:
   ```bash
   cd backend
   celery -A core worker -l info
   ```

3. **Start Celery Beat** (for scheduled tasks):
   ```bash
   cd backend
   celery -A core beat -l info
   ```

## Production Deployment

For production deployment, consider:

1. Using a process manager like Supervisor or systemd to manage Celery workers
2. Scaling worker count based on load requirements
3. Implementing monitoring and alerting for task failures
4. Using a dedicated Redis instance with persistence enabled

## Best Practices

1. **Task Idempotency**: Tasks should be idempotent (can be run multiple times without side effects)
2. **Error Handling**: Include proper error handling in tasks
3. **Logging**: Use logging to track task execution and errors
4. **Transaction Isolation**: Use Django's transaction atomicity where appropriate
5. **Task Design**: Keep tasks small and focused on specific operations
