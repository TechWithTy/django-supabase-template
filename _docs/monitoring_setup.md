# Prometheus and Grafana Monitoring Setup

## Overview

This document describes the monitoring setup for the Django Supabase Template, which includes Prometheus for metrics collection and Grafana for visualization. The monitoring system tracks API usage, credit operations, user activity, and system resources.

## Architecture

The monitoring system consists of the following components:

1. **Django Monitoring App**: Collects and exposes metrics about API usage, credit operations, and anomalies
2. **Prometheus**: Scrapes and stores metrics from the Django application
3. **Grafana**: Visualizes the metrics in dashboards and provides alerting capabilities
4. **Node Exporter**: Collects system-level metrics (CPU, memory, disk, network)
5. **cAdvisor**: Collects container-level metrics from Docker

## Available Metrics

### API Metrics
- `api_requests_total`: Total count of API requests by endpoint, method, and status
- `api_request_latency_seconds`: API request latency in seconds
- `api_error_rate`: Error rate for API endpoints

### Credit System Metrics
- `credit_usage_total`: Total credit usage by operation and user
- `credit_operation_latency_seconds`: Latency of credit operations

### User Activity Metrics
- `user_sessions`: Number of active user sessions by authentication method
- `active_users`: Number of active users by timeframe (1m, 5m, 15m, 1h, 1d)

### System Metrics
- `system_memory_usage`: System memory usage by type (total, used, free)
- `system_cpu_usage`: CPU usage by type (user, system, idle)
- `cache_hit_ratio`: Cache hit ratio by cache type
- `cache_size`: Cache size by cache type
- `db_query_latency_seconds`: Database query latency by operation and table
- `db_connection_pool_size`: Database connection pool size by database

### Anomaly Detection
- `anomaly_detection_triggered_total`: Count of anomaly detections by endpoint and reason

## Setup and Configuration

### Running the Monitoring Stack

To start the monitoring stack, run:

```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

This will start Prometheus, Grafana, Node Exporter, and cAdvisor.

### Accessing the Services

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (default login: admin/admin)
- **cAdvisor**: http://localhost:8080
- **Node Exporter**: http://localhost:9100/metrics

### Grafana Dashboards

The monitoring setup includes a pre-configured dashboard for API monitoring:

1. **Django API Monitoring**: Visualizes API requests, latency, error rates, credit usage, and anomaly detections

## Integration with Django

The Django application has a monitoring app that collects and exposes metrics. This app includes:

1. **Middleware**: `PrometheusMonitoringMiddleware` tracks API requests, latencies, and errors
2. **Views**: Exposes metrics for Prometheus to scrape at `/monitoring/metrics/`
3. **Utilities**: 
   - `track_latency`: Context manager to track operation latency
   - `instrument`: Decorator to instrument functions with metrics
   - `detect_anomalies`: Context manager to detect anomalies in API operations
   - `track_db_query`: Context manager to track database query latency

### Using the Utilities in Your Code

```python
# Track API latency
from apps.monitoring.utils import track_latency
from apps.monitoring.metrics import API_REQUEST_LATENCY

with track_latency(API_REQUEST_LATENCY, endpoint='users', method='GET'):
    # Your API code here

# Instrument a function
from apps.monitoring.utils import instrument

@instrument(API_REQUEST_LATENCY, endpoint='users', method='GET')
def my_view(request):
    # View code here

# Detect anomalies
from apps.monitoring.utils import detect_anomalies

with detect_anomalies('users', latency_threshold=0.5):
    # Your API operation here

# Track database queries
from apps.monitoring.utils import track_db_query

with track_db_query('select', 'users_userprofile'):
    # Your database query here
```

## Alerts

The monitoring system includes the following alerts:

1. **HighErrorRate**: Triggered when the error rate for an endpoint exceeds 5% for 5 minutes
2. **HighLatency**: Triggered when the 95th percentile of response time for an endpoint exceeds 1s for 5 minutes
3. **AnomalyDetected**: Triggered when anomalies are detected in API operations

## Extending the Monitoring System

### Adding New Metrics

To add new metrics, update the `metrics.py` file in the monitoring app:

```python
from prometheus_client import Counter, Histogram, Gauge

# Define a new counter
MY_NEW_COUNTER = Counter(
    'my_new_metric_total',
    'Description of my new metric',
    ['label1', 'label2']
)

# Increment the counter in your code
MY_NEW_COUNTER.labels(label1='value1', label2='value2').inc()
```

### Adding New Dashboards

To add new dashboards to Grafana:

1. Create a new dashboard in Grafana UI
2. Export the dashboard as JSON
3. Save the JSON file in the `config/grafana/provisioning/dashboards` directory
4. Update the dashboard provider configuration if needed

## Troubleshooting

### Common Issues

1. **Metrics not showing up in Prometheus**:
   - Check that the Django app is running and accessible
   - Verify that the metrics endpoint is accessible at `/monitoring/metrics/`
   - Check the Prometheus targets page for errors

2. **Dashboards not loading in Grafana**:
   - Verify that Prometheus is configured as a data source in Grafana
   - Check the Grafana logs for errors
   - Ensure dashboard JSON files are correctly formatted

### Logs

- Prometheus logs: `docker logs prometheus`
- Grafana logs: `docker logs grafana`
- cAdvisor logs: `docker logs cadvisor`
- Node Exporter logs: `docker logs node-exporter`
