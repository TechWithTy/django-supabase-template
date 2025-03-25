from django.conf import settings
from prometheus_client import Counter, Gauge, Histogram
import time
from functools import wraps
import logging

logger = logging.getLogger("credits.metrics")

# Define Prometheus metrics
CREDIT_TRANSACTIONS_TOTAL = Counter(
    'credit_transactions_total',
    'Total number of credit transactions',
    ['transaction_type', 'endpoint']
)

CREDIT_TRANSACTION_AMOUNT = Histogram(
    'credit_transaction_amount',
    'Distribution of credit transaction amounts',
    ['transaction_type'],
    buckets=[1, 5, 10, 20, 50, 100, 200, 500, 1000]
)

CREDIT_BALANCE_TOTAL = Gauge(
    'credit_balance_total',
    'Total credit balance across all users'
)

CREDIT_ACTIVE_HOLDS_TOTAL = Gauge(
    'credit_holds_active_total',
    'Total number of active credit holds'
)

CREDIT_HOLDS_AMOUNT_TOTAL = Gauge(
    'credit_holds_amount_total',
    'Total amount of credits on hold'
)

CREDIT_OPERATION_DURATION = Histogram(
    'credit_operation_duration_seconds',
    'Duration of credit operations',
    ['operation'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
)

CREDIT_OPERATION_FAILURES = Counter(
    'credit_operation_failures_total',
    'Total number of credit operation failures',
    ['operation', 'reason']
)


def track_credit_operation(operation_name):
    """
    Decorator to track the duration of credit operations and record failures.
    
    Args:
        operation_name: Name of the credit operation being performed
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            error_reason = None
            
            try:
                result = func(*args, **kwargs)
                success = True if result is not None else False
                if not success:
                    error_reason = "insufficient_credits"
                return result
            except Exception as e:
                error_reason = type(e).__name__
                logger.exception(f"Credit operation {operation_name} failed: {e}")
                raise
            finally:
                duration = time.time() - start_time
                
                # Record operation duration
                CREDIT_OPERATION_DURATION.labels(operation=operation_name).observe(duration)
                
                # Record failure if applicable
                if not success:
                    CREDIT_OPERATION_FAILURES.labels(
                        operation=operation_name,
                        reason=error_reason or "unknown"
                    ).inc()
                    
        return wrapper
    return decorator


def record_transaction_metrics(transaction):
    """
    Record metrics for a credit transaction.
    
    Args:
        transaction: A CreditTransaction instance
    """
    # Track transaction count
    CREDIT_TRANSACTIONS_TOTAL.labels(
        transaction_type=transaction.transaction_type,
        endpoint=transaction.endpoint or "unknown"
    ).inc()
    
    # Track transaction amount distribution
    CREDIT_TRANSACTION_AMOUNT.labels(
        transaction_type=transaction.transaction_type
    ).observe(abs(transaction.amount))


def update_balance_metrics():
    """
    Update the total credit balance gauge.
    Should be called periodically or after significant changes.
    """
    from apps.users.models import UserProfile
    
    try:
        # Calculate total credit balance across all users
        total_balance = UserProfile.objects.all().aggregate(
            total=models.Sum('credits_balance')
        )['total'] or 0
        
        CREDIT_BALANCE_TOTAL.set(total_balance)
    except Exception as e:
        logger.exception(f"Failed to update balance metrics: {e}")


def update_hold_metrics():
    """
    Update metrics related to credit holds.
    Should be called periodically or after significant changes.
    """
    from apps.credits.models import CreditHold
    
    try:
        # Count active holds
        active_holds_count = CreditHold.objects.filter(is_active=True).count()
        CREDIT_ACTIVE_HOLDS_TOTAL.set(active_holds_count)
        
        # Calculate total amount on hold
        total_hold_amount = CreditHold.objects.filter(is_active=True).aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        CREDIT_HOLDS_AMOUNT_TOTAL.set(total_hold_amount)
    except Exception as e:
        logger.exception(f"Failed to update hold metrics: {e}")
