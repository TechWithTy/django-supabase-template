from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.core.cache import cache
import psutil
import threading
import time

from apps.credits.models import CreditTransaction
from .metrics import (
    CREDIT_USAGE_COUNTER,
    USER_SESSIONS,
    ACTIVE_USERS,
    SYSTEM_MEMORY_USAGE,
    SYSTEM_CPU_USAGE,
    CACHE_HIT_RATIO,
    CACHE_SIZE,
    DB_CONNECTION_POOL_SIZE
)

# User activity tracking
@receiver(user_logged_in)
def track_user_login(sender, request, user, **kwargs):
    """Track user login events for monitoring"""
    auth_method = getattr(request, 'auth_method', 'default')
    USER_SESSIONS.labels(auth_method=auth_method).inc()
    
    # Update active users counts
    _update_active_users()

@receiver(user_logged_out)
def track_user_logout(sender, request, user, **kwargs):
    """Track user logout events for monitoring"""
    # Update active users counts
    _update_active_users()

# Credit transaction tracking
@receiver(post_save, sender=CreditTransaction)
def track_credit_transaction(sender, instance, created, **kwargs):
    """Track credit transactions for monitoring"""
    if created and instance.amount < 0:  # Only count credit usage, not additions
        CREDIT_USAGE_COUNTER.labels(
            operation=instance.description,
            user_id=str(instance.user_id)
        ).inc(abs(instance.amount))  # Use absolute value for the counter

# Helper functions
def _update_active_users():
    """Update the active users gauge based on session data"""
    # This is a simplified implementation - in a real app, you'd query your session backend
    # For demonstration, we'll set some example values
    active_1m = cache.get('active_users_1m', 0)
    active_5m = cache.get('active_users_5m', 0) 
    active_15m = cache.get('active_users_15m', 0)
    active_1h = cache.get('active_users_1h', 0)
    active_1d = cache.get('active_users_1d', 0)
    
    ACTIVE_USERS.labels(timeframe='1m').set(active_1m)
    ACTIVE_USERS.labels(timeframe='5m').set(active_5m)
    ACTIVE_USERS.labels(timeframe='15m').set(active_15m)
    ACTIVE_USERS.labels(timeframe='1h').set(active_1h)
    ACTIVE_USERS.labels(timeframe='1d').set(active_1d)

# System monitoring background thread
def _monitor_system_resources():
    """Background thread to monitor system resources"""
    while True:
        # Memory metrics
        memory = psutil.virtual_memory()
        SYSTEM_MEMORY_USAGE.labels(type='total').set(memory.total)
        SYSTEM_MEMORY_USAGE.labels(type='used').set(memory.used)
        SYSTEM_MEMORY_USAGE.labels(type='free').set(memory.free)
        
        # CPU metrics
        cpu = psutil.cpu_times_percent(interval=1)
        SYSTEM_CPU_USAGE.labels(type='user').set(cpu.user)
        SYSTEM_CPU_USAGE.labels(type='system').set(cpu.system)
        SYSTEM_CPU_USAGE.labels(type='idle').set(cpu.idle)
        
        # Cache metrics (example values - would need to be adapted for your cache backend)
        CACHE_HIT_RATIO.labels(cache_type='default').set(cache.get('cache_hit_ratio', 0.9))
        CACHE_SIZE.labels(cache_type='default').set(cache.get('cache_size', 1024 * 1024))
        
        # Database connection pool
        DB_CONNECTION_POOL_SIZE.labels(database='default').set(cache.get('db_pool_size', 10))
        DB_CONNECTION_POOL_SIZE.labels(database='supabase').set(cache.get('supabase_db_pool_size', 5))
        
        time.sleep(15)  # Update every 15 seconds

# Start the background monitoring thread when Django starts
system_monitor_thread = threading.Thread(target=_monitor_system_resources, daemon=True)
system_monitor_thread.start()
