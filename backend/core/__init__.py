# This file is required to make Python treat the directory as a package

# Configure Celery
from .celery import app as celery_app

__all__ = ('celery_app',)
