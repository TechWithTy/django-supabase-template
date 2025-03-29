# User Behavior Tracking and API Anomaly Detection

## Overview

This documentation explains how user behavior tracking (event logging) and API anomaly detection are implemented in the Django-Supabase Template. These features provide powerful insights into user activity patterns and help identify potential issues before they impact your application.

## Architecture

The monitoring and analytics system is built on the following components:

1. **Prometheus Metrics**: A comprehensive set of metrics collected using the Prometheus client library
2. **Monitoring Middleware**: Django middleware that automatically collects metrics for all API requests
3. **Utility Functions**: Helper functions and context managers for custom instrumentation
4. **Grafana Dashboard**: Visualization of collected metrics

## Implementation Details

### User Behavior Tracking

User behavior tracking is implemented through a combination of automatic request monitoring and explicit event logging:

#### Automatic Request Tracking

All API requests are automatically tracked by the `PrometheusMonitoringMiddleware` which captures:

- Endpoint accessed
- HTTP method used
- Response status code
- Request latency

This middleware is added to the Django `MIDDLEWARE` setting and requires no additional configuration to work.

#### User Activity Metrics

The system tracks several user activity metrics:

```python
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
```

These metrics are automatically updated through signal handlers that respond to user login/logout events and session creation/destruction.

#### Custom Event Tracking

For more specific user behavior tracking, you can use the utility functions to instrument your code:

```python
from apps.monitoring.utils import instrument
from apps.monitoring.metrics import USER_SESSIONS

# Track user login with authentication method
@instrument(USER_SESSIONS, auth_method='password')
def password_login_view(request):
    # Login logic here
    pass
```

### API Anomaly Detection

API anomaly detection helps identify unusual patterns in API usage that might indicate problems or security issues.

#### Automatic Anomaly Detection

The middleware automatically detects and logs several types of anomalies:

1. **Server Errors**: Any 5xx response triggers an anomaly alert
2. **High Latency**: Requests taking longer than a configured threshold
3. **Error Rate Spikes**: Sudden increases in error rates for specific endpoints

These anomalies are tracked with the following metrics:

```python
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
```

#### Custom Anomaly Detection

You can add custom anomaly detection to your code using the `detect_anomalies` context manager:

```python
from apps.monitoring.utils import detect_anomalies

def credit_charging_view(request):
    # Critical operation that should be monitored for anomalies
    with detect_anomalies('credit_charging', latency_threshold=0.5, error_threshold=0.01):
        # Charge credits logic
        perform_credit_operation()
        
    return response
```

## How to Test

### Testing User Behavior Tracking

#### Manual Testing

1. Start your Django application and the monitoring stack:

```bash
# Start Django
python manage.py runserver

# Start the monitoring stack in another terminal
docker-compose -f docker-compose.monitoring.yml up -d
```

2. Generate some user activity:
   - Log in and out of the application several times
   - Navigate to different API endpoints
   - Perform various user actions

3. View the metrics in Grafana at http://localhost:3000
   - Check the "Active Users" panel
   - Look at the "API Request Rate" panel filtered by endpoint

#### Automated Testing

You can write unit tests for your user behavior tracking using the Django test client:

```python
import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from prometheus_client import REGISTRY

User = get_user_model()

class UserBehaviorTrackingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
    
    def test_user_session_tracking(self):
        # Get initial counter value
        initial_count = self._get_counter_value('user_sessions_total', {'auth_method': 'password'})
        
        # Perform login
        login_url = reverse('users:login')
        response = self.client.post(login_url, {
            'username': 'testuser',
            'password': 'testpassword123'
        })
        
        # Check that counter incremented
        new_count = self._get_counter_value('user_sessions_total', {'auth_method': 'password'})
        self.assertEqual(new_count - initial_count, 1)
    
    def _get_counter_value(self, name, labels):
        # Helper method to get prometheus counter value
        counter = REGISTRY.get_sample_value(name, labels)
        return counter or 0
```

### Testing API Anomaly Detection

#### Manual Testing

1. Start your Django application and the monitoring stack as described above

2. Generate some anomalies:
   - Make requests to non-existent endpoints (404 errors)
   - Trigger server errors by providing invalid data to endpoints
   - Make a large number of rapid requests to simulate unusual traffic

3. View the anomaly metrics in Grafana:
   - Check the "Error Rate" panel
   - Look at the "Anomaly Detection" panel
   - Check the "API Latency" panel for high response times

#### Automated Testing

You can write unit tests for anomaly detection:

```python
from django.test import TestCase, Client
from django.urls import reverse
from prometheus_client import REGISTRY
import time

class AnomalyDetectionTests(TestCase):
    def setUp(self):
        self.client = Client()
    
    def test_server_error_anomaly_detection(self):
        # Get initial anomaly counter
        initial_count = self._get_counter_value('anomaly_detection_triggered_total', 
                                               {'endpoint': 'test', 'reason': 'server_error'})
        
        # Trigger a server error (this needs a specific endpoint that will cause a 500 error)
        error_url = reverse('monitoring:test_error')
        response = self.client.get(error_url)
        self.assertEqual(response.status_code, 500)
        
        # Check that anomaly counter incremented
        new_count = self._get_counter_value('anomaly_detection_triggered_total', 
                                           {'endpoint': 'test', 'reason': 'server_error'})
        self.assertEqual(new_count - initial_count, 1)
    
    def test_high_latency_anomaly_detection(self):
        # Get initial anomaly counter
        initial_count = self._get_counter_value('anomaly_detection_triggered_total', 
                                               {'endpoint': 'test', 'reason': 'high_latency'})
        
        # Make request to slow endpoint (this needs a specific endpoint that will be slow)
        slow_url = reverse('monitoring:test_slow')
        response = self.client.get(slow_url)
        self.assertEqual(response.status_code, 200)
        
        # Check that anomaly counter incremented
        new_count = self._get_counter_value('anomaly_detection_triggered_total', 
                                           {'endpoint': 'test', 'reason': 'high_latency'})
        self.assertEqual(new_count - initial_count, 1)
    
    def _get_counter_value(self, name, labels):
        # Helper method to get prometheus counter value
        counter = REGISTRY.get_sample_value(name, labels)
        return counter or 0
```

## Integration with the Credit System

The tracking system integrates with the credit-based function execution system to monitor credit usage:

```python
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
```

To track credit usage in your credit-based views:

```python
from apps.monitoring.metrics import CREDIT_USAGE_COUNTER
from apps.monitoring.utils import track_latency, CREDIT_OPERATION_LATENCY

@with_credits(cost=5)
def expensive_operation(request):
    # Track credit usage
    CREDIT_USAGE_COUNTER.labels(
        operation='expensive_operation',
        user_id=str(request.user.id)
    ).inc(5)  # Increment by cost
    
    with track_latency(CREDIT_OPERATION_LATENCY, operation='expensive_operation'):
        # Perform the expensive operation
        result = perform_expensive_calculation()
    
    return result
```

## Best Practices

1. **Add Context with Labels**: Always use descriptive labels for metrics to enable fine-grained analysis

2. **Track Important User Events**: Instrument critical user flows like sign-up, purchase, content creation

3. **Set Appropriate Thresholds**: Configure anomaly detection thresholds based on your application's normal behavior

4. **Regular Review**: Periodically review the metrics dashboard to identify trends and potential issues

5. **Add Custom Metrics**: Extend the system with application-specific metrics that are relevant to your business

## Resources

- [Prometheus Documentation](https://prometheus.io/docs/introduction/overview/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Django-Prometheus](https://github.com/korfuri/django-prometheus)
- [Metrics Best Practices](https://prometheus.io/docs/practices/naming/)
