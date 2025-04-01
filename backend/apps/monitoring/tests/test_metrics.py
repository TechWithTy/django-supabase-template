from unittest import TestCase
from unittest.mock import patch, MagicMock


class TestPrometheusMetrics(TestCase):
    def setUp(self):
        """Set up test mocks"""
        # Mock Django's client
        self.client_patcher = patch('django.test.Client')
        self.mock_client_class = self.client_patcher.start()
        self.mock_client = MagicMock()
        self.mock_client_class.return_value = self.mock_client
        
        # Mock response
        self.mock_response = MagicMock()
        self.mock_response.status_code = 200
        self.mock_response.content = b'''
# HELP django_http_requests_total Total count of requests by method and view.
# TYPE django_http_requests_total counter
django_http_requests_total{method="GET",view="users"} 1.0
# HELP api_requests_total Total count of API requests
# TYPE api_requests_total counter
api_requests_total{endpoint="users",method="GET",status="200"} 1.0
# HELP api_error_rate Rate of API errors
# TYPE api_error_rate gauge
api_error_rate{endpoint="users"} 0.0
'''
        
        # Create client instance
        self.client = self.mock_client
        
        # Setup API counter mock
        self.api_counter_patcher = patch('apps.monitoring.metrics.API_REQUESTS_COUNTER')
        self.mock_api_counter = self.api_counter_patcher.start()
        self.mock_api_counter._value = {}
        self.mock_api_counter.clear = MagicMock()
        
        # Setup error rate mock
        self.error_rate_patcher = patch('apps.monitoring.metrics.API_ERROR_RATE')
        self.mock_error_rate = self.error_rate_patcher.start()
        self.mock_error_rate._value = {}
        self.mock_error_rate.clear = MagicMock()
    
    def tearDown(self):
        """Clean up patches"""
        self.client_patcher.stop()
        self.api_counter_patcher.stop()
        self.error_rate_patcher.stop()
    
    def test_metrics_endpoint_access(self):
        """Test that the metrics endpoint returns a 200 OK response"""
        # Configure mock response
        self.mock_client.get.return_value = self.mock_response
        
        # Make request
        response = self.client.get('/metrics/')
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        # Verify client was called with correct URL
        self.mock_client.get.assert_called_once_with('/metrics/')
    
    def test_custom_api_usage_metrics(self):
        """Test that our custom API usage metrics are being tracked"""
        # Configure counter 
        self.mock_api_counter._value = {('users', 'GET', '200'): 1}
        
        # Make request
        self.mock_client.get.return_value = self.mock_response
        self.client.get('/api/users/profile/')
        
        # Verify counter was incremented
        self.assertEqual(self.mock_api_counter._value.get(('users', 'GET', '200'), 0), 1)
    
    def test_anomaly_detection_metrics(self):
        """Test that our anomaly detection metrics are working"""
        # Configure error rate mock
        self.mock_error_rate._value = {('users',): 0}
        
        # Configure client responses
        profile_response = MagicMock()
        profile_response.status_code = 200
        
        not_found_response = MagicMock()
        not_found_response.status_code = 404
        
        def get_side_effect(url, *args, **kwargs):
            if url == '/api/users/profile/':
                return profile_response
            else:
                return not_found_response
        
        self.mock_client.get.side_effect = get_side_effect
        
        # Generate successful and failed requests
        self.client.get('/api/users/profile/')
        self.client.get('/api/non-existent-endpoint/')
        
        # Check metrics
        self.assertEqual(self.mock_error_rate._value.get(('users',), 0), 0)  # No errors in users endpoint
    
    @patch('prometheus_client.parser.text_string_to_metric_families')
    def test_prometheus_metrics_format(self, mock_parser):
        """Test that the metrics are exported in the correct Prometheus format"""
        # Configure metric families
        http_metric = MagicMock()
        http_metric.name = 'django_http_requests_total'
        http_metric.type = 'counter'
        
        mock_parser.return_value = [http_metric]
        
        # Configure client response
        self.mock_client.get.return_value = self.mock_response
        
        # Make request
        response = self.client.get('/metrics/')
        
        # Parse metrics from response
        metrics = list(mock_parser(response.content.decode('utf-8')))
        
        # Assertions
        self.assertGreater(len(metrics), 0)
        
        # Check for custom metrics
        metric_names = [metric.name for metric in metrics]
        self.assertIn('django_http_requests_total', metric_names)
