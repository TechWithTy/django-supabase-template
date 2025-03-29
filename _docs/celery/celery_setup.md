# Celery Implementation Guide

## Overview

This document provides a comprehensive guide to the Celery implementation in the Django-Supabase template. Celery is an asynchronous task queue/job queue based on distributed message passing that is used for handling background tasks and scheduled operations.

## Architecture

The Celery implementation in this project follows a standard architecture:

- **Broker**: Redis is used as the message broker for queuing tasks
- **Workers**: Celery workers process tasks from the queue
- **Beat**: Celery beat schedules periodic tasks
- **Result Backend**: Redis is also used to store task results (when needed)

## Configuration

The Celery configuration is defined in `backend/core/celery.py`. Key settings include:

```python
# Set the default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
```

Environment variables for Celery configuration are defined in `.env` and `.env` files:

```
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

## Task Definition

Tasks are defined in `tasks.py` files within each Django app. For example, in the credits app:

```python
from celery import shared_task
import logging
from datetime import datetime

logger = logging.getLogger('credits')

@shared_task
def cleanup_expired_credit_holds():
    """Task to clean up expired credit holds."""
    now = datetime.now()
    logger.info(f"[{now}] Running cleanup for expired credit holds")

    # Implementation code here

    return "Cleanup completed"
```

## Scheduling Periodic Tasks

Periodic tasks are configured in the `CELERY_BEAT_SCHEDULE` setting in `settings.py`:

```python
CELERY_BEAT_SCHEDULE = {
    'cleanup-expired-credit-holds': {
        'task': 'apps.credits.tasks.cleanup_expired_credit_holds',
        'schedule': crontab(minute='0', hour='*/3'),  # Run every 3 hours
    },
}
```

## Running Celery

### Development Environment

To run Celery in the development environment:

1. Start the Redis broker:

   ```bash
   docker-compose up redis
   ```

2. Start a Celery worker:

   ```bash
   cd backend
   celery -A core worker -l info
   ```

3. Start Celery beat for scheduled tasks (in a separate terminal):
   ```bash
   cd backend
   celery -A core beat -l info
   ```

### Production Environment

In production, Celery is managed through Docker Compose as defined in `docker-compose.prod.yml`:

```yaml
# Celery worker for async tasks
celery-worker:
  image: ghcr.io/${GITHUB_REPOSITORY}:production
  restart: unless-stopped
  command: celery -A core worker -l info
  depends_on:
    - redis
    - backend
  env_file:
    - .env

# Celery beat for scheduled tasks
celery-beat:
  image: ghcr.io/${GITHUB_REPOSITORY}:production
  restart: unless-stopped
  command: celery -A core beat -l info
  depends_on:
    - redis
    - backend
  env_file:
    - .env
```

## Testing Celery Tasks

### Manual Testing

To manually test a Celery task, you can create a simple script:

```python
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from apps.credits.tasks import cleanup_expired_credit_holds

if __name__ == '__main__':
    print("Testing Celery task...")
    result = cleanup_expired_credit_holds.apply()
    print(f"Task completed with result: {result}")
```

### Unit Testing

For unit testing Celery tasks, use the `CELERY_TASK_ALWAYS_EAGER` setting:

```python
from django.test import TestCase, override_settings
from apps.credits.tasks import cleanup_expired_credit_holds

@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class CeleryTasksTestCase(TestCase):
    def test_cleanup_expired_credit_holds(self):
        result = cleanup_expired_credit_holds.delay()
        self.assertEqual(result.get(), "Cleanup completed")
```

## Monitoring

Celery tasks can be monitored using Flower, a web-based tool for monitoring Celery:

```bash
celery -A core flower --port=5555
```

In production, Flower is configured in `docker-compose.prod.yml`:

```yaml
flower:
  image: ghcr.io/${GITHUB_REPOSITORY}:production
  restart: unless-stopped
  command: celery -A core flower --port=5555
  ports:
    - "5555:5555"
  depends_on:
    - redis
    - celery-worker
  env_file:
    - .env
```

## Best Practices

1. **Task Idempotency**: Design tasks to be idempotent (can be run multiple times without side effects)
2. **Error Handling**: Implement proper error handling and retries for tasks
3. **Task Timeouts**: Set appropriate timeouts for long-running tasks
4. **Task Serialization**: Use JSON serialization for better compatibility
5. **Monitoring**: Implement monitoring and alerting for task failures

## Common Issues and Troubleshooting

1. **Connection Errors**: Ensure Redis is running and accessible
2. **Task Not Found**: Verify task imports and module paths
3. **Task Timeouts**: Increase timeout settings for long-running tasks
4. **Memory Issues**: Monitor worker memory usage and implement proper resource limits

## Additional Resources

- [Celery Documentation](https://docs.celeryproject.org/)
- [Django Celery Integration](https://docs.celeryproject.org/en/stable/django/first-steps-with-django.html)
- [Redis Documentation](https://redis.io/documentation)
