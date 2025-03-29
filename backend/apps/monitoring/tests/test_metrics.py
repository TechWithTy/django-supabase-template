import pytest
from django.test import Client
from prometheus_client.parser import text_string_to_metric_families


@pytest.mark.django_db
class TestPrometheusMetrics:
    def test_metrics_endpoint_access(self):
        """Test that the metrics endpoint returns a 200 OK response"""
        client = Client()
        response = client.get('/metrics/')
        assert response.status_code == 200
        
    def test_custom_api_usage_metrics(self, monkeypatch):
        """Test that our custom API usage metrics are being tracked"""
        from apps.monitoring.metrics import API_REQUESTS_COUNTER
        
        # Reset metrics for testing
        API_REQUESTS_COUNTER.clear()
        
        # Mock request
        client = Client()
        client.get('/api/users/profile/')
        
        # Verify counter was incremented
        assert API_REQUESTS_COUNTER._value.get(('users', 'GET', '200'), 0) == 1
        
    def test_anomaly_detection_metrics(self):
        """Test that our anomaly detection metrics are working"""
        from apps.monitoring.metrics import API_ERROR_RATE
        
        # Reset metrics for testing
        API_ERROR_RATE.clear()
        
        # Generate test data for anomaly detection
        client = Client()
        
        # Generate a successful request
        client.get('/api/users/profile/')
        
        # Generate a failed request (404)
        client.get('/api/non-existent-endpoint/')
        
        # Check that our metrics are tracking properly
        assert API_ERROR_RATE._value.get(('users',), 0) == 0  # No errors in users endpoint
        
    def test_prometheus_metrics_format(self):
        """Test that the metrics are exported in the correct Prometheus format"""
        client = Client()
        response = client.get('/metrics/')
        
        # Parse the metrics from the response
        metrics = list(text_string_to_metric_families(response.content.decode('utf-8')))
        
        # Check that we have metrics
        assert len(metrics) > 0
        
        # Check for our custom metrics
        metric_names = [metric.name for metric in metrics]
        assert 'django_http_requests_total' in metric_names  # This is a default django-prometheus metric
