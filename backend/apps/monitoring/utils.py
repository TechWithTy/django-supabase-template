import time
import functools
from contextlib import contextmanager

from .metrics import (
    DB_QUERY_LATENCY,
    ANOMALY_DETECTION_TRIGGERED
)


@contextmanager
def track_latency(metric, **labels):
    """
    Context manager to track operation latency using Prometheus histograms.
    
    Example:
        with track_latency(API_REQUEST_LATENCY, endpoint='users', method='GET'):
            # Your operation here
    """
    start_time = time.time()
    try:
        yield
    finally:
        latency = time.time() - start_time
        metric.labels(**labels).observe(latency)


def instrument(metric, **labels):
    """
    Decorator to instrument a function with Prometheus metrics.
    
    Example:
        @instrument(API_REQUEST_LATENCY, endpoint='users', method='GET')
        def my_view(request):
            # View code here
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with track_latency(metric, **labels):
                return func(*args, **kwargs)
        return wrapper
    return decorator


@contextmanager
def detect_anomalies(endpoint, latency_threshold=1.0, error_threshold=0.05):
    """
    Context manager to detect anomalies in API operations.
    
    Example:
        with detect_anomalies('users', latency_threshold=0.5):
            # Your API operation here
    """
    start_time = time.time()
    try:
        yield
    except Exception:
        # Trigger anomaly detection on exception
        ANOMALY_DETECTION_TRIGGERED.labels(
            endpoint=endpoint,
            reason='exception'
        ).inc()
        raise
    finally:
        latency = time.time() - start_time
        
        # Check for latency anomalies
        if latency > latency_threshold:
            ANOMALY_DETECTION_TRIGGERED.labels(
                endpoint=endpoint,
                reason='high_latency'
            ).inc()


@contextmanager
def track_db_query(operation, table):
    """
    Context manager to track database query latency.
    
    Example:
        with track_db_query('select', 'users_userprofile'):
            # Your database query here
    """
    start_time = time.time()
    try:
        yield
    finally:
        latency = time.time() - start_time
        DB_QUERY_LATENCY.labels(
            operation=operation,
            table=table
        ).observe(latency)
