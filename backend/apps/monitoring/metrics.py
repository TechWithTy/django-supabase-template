from prometheus_client import Counter, Histogram, Gauge, REGISTRY

# Create a custom registry to avoid conflicts
try:
    # Try to unregister existing metrics if they exist
    for metric in [
        'api_requests_total', 'api_request_latency_seconds', 
        'credit_usage_total', 'credit_operation_latency_seconds', 
        'active_users', 'user_sessions_total', 
        'api_error_rate', 'api_response_time_threshold', 
        'anomaly_detection_triggered_total', 
        'db_query_latency_seconds', 'db_connection_pool_size', 
        'cache_hit_ratio', 'cache_size_bytes', 
        'system_memory_usage_bytes', 'system_cpu_usage_percent'
    ]:
        if metric in REGISTRY._names_to_collectors:
            REGISTRY.unregister(REGISTRY._names_to_collectors[metric])
except Exception:
    pass

# API Usage Metrics
API_REQUESTS_COUNTER = Counter(
    'api_requests_total',
    'Total count of API requests',
    ['endpoint', 'method', 'status']
)

API_REQUEST_LATENCY = Histogram(
    'api_request_latency_seconds',
    'API request latency in seconds',
    ['endpoint', 'method'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

# Credit-Based Operation Metrics
CREDIT_USAGE_COUNTER = Counter(
    'credit_usage_total',
    'Total credits used by operations',
    ['operation', 'user_id']
)

CREDIT_OPERATION_LATENCY = Histogram(
    'credit_operation_latency_seconds',
    'Credit operation latency in seconds',
    ['operation'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

# User Activity Metrics
ACTIVE_USERS = Gauge(
    'active_users',
    'Number of active users',
    ['timeframe']  # e.g., '1m', '5m', '15m', '1h', '1d'
)

USER_SESSIONS = Counter(
    'user_sessions_total',
    'Total number of user sessions',
    ['auth_method']
)

# Anomaly Detection Metrics
API_ERROR_RATE = Gauge(
    'api_error_rate',
    'Rate of API errors',
    ['endpoint']
)

API_RESPONSE_TIME_THRESHOLD = Gauge(
    'api_response_time_threshold',
    'Threshold for abnormal API response times',
    ['endpoint']
)

ANOMALY_DETECTION_TRIGGERED = Counter(
    'anomaly_detection_triggered_total',
    'Total number of times anomaly detection was triggered',
    ['endpoint', 'reason']
)

# Database Metrics
DB_QUERY_LATENCY = Histogram(
    'db_query_latency_seconds',
    'Database query latency in seconds',
    ['operation', 'table'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0)
)

DB_CONNECTION_POOL_SIZE = Gauge(
    'db_connection_pool_size',
    'Current size of the database connection pool',
    ['database']
)

# Cache Metrics
CACHE_HIT_RATIO = Gauge(
    'cache_hit_ratio',
    'Cache hit ratio',
    ['cache_type']
)

CACHE_SIZE = Gauge(
    'cache_size_bytes',
    'Current size of the cache in bytes',
    ['cache_type']
)

# System Resource Metrics
SYSTEM_MEMORY_USAGE = Gauge(
    'system_memory_usage_bytes',
    'System memory usage in bytes',
    ['type']  # e.g., 'used', 'free', 'total'
)

SYSTEM_CPU_USAGE = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage',
    ['type']  # e.g., 'user', 'system', 'idle'
)
