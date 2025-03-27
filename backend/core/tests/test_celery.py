import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from core.celery import debug_task

if __name__ == '__main__':
    # Call the debug task synchronously for testing
    print("Testing Celery debug task...")
    result = debug_task.apply()
    print("Task completed!")
