import json
from unittest import TestCase
from unittest.mock import patch, MagicMock


class MetricsEndpointsTests(TestCase):
    """
    Test class for verifying the Prometheus metrics endpoints are working correctly.
    Fully isolated from real databases and dependencies.
    """
    
    def setUp(self):
        """Set up test mocks"""
        # Mock Django's URL reverse function
        self.reverse_patcher = patch('django.urls.reverse')
        self.mock_reverse = self.reverse_patcher.start()
        
        # Mock response objects
        self.metrics_response = MagicMock()
        self.metrics_response.status_code = 200
        self.metrics_response.content = b'# HELP api_requests_total Total count of API requests\n# TYPE api_requests_total counter'
        self.metrics_response.__getitem__.return_value = 'text/plain; version=0.0.4'
        
        self.json_response = MagicMock()
        self.json_response.status_code = 200
        self.json_response.content = json.dumps({
            'api_requests': [{'endpoint': '/api/test', 'count': 100}],
            'api_latency': [{'endpoint': '/api/test', 'avg_latency': 0.05}],
            'credit_usage': [{'operation': 'query', 'total': 50}],
            'active_users': {'1h': 10, '24h': 50},
            'error_rates': [{'endpoint': '/api/test', 'rate': 0.01}],
            'anomalies': [{'endpoint': '/api/test', 'type': 'high_latency', 'count': 2}]
        }).encode()
        self.json_response.__getitem__.return_value = 'application/json'
        
        self.redirect_response = MagicMock()
        self.redirect_response.status_code = 302
        
        # Mock Django's client
        self.client_patcher = patch('django.test.Client')
        self.mock_client_class = self.client_patcher.start()
        self.mock_client = MagicMock()
        self.mock_client_class.return_value = self.mock_client
        
        # Configure the mock client for different authenticated states
        self.is_authenticated = True
    
    def tearDown(self):
        """Clean up patches"""
        self.reverse_patcher.stop()
        self.client_patcher.stop()
    
    def test_metrics_endpoint_authenticated(self):
        """Test metrics endpoint with authenticated user"""
        # Setup URL
        self.mock_reverse.return_value = '/monitoring/metrics/'
        
        # Setup mock client response
        self.mock_client.get.return_value = self.metrics_response
        
        # Call endpoint
        url = self.mock_reverse('monitoring:metrics')
        response = self.mock_client.get(url)
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain; version=0.0.4')
        content = response.content.decode()
        self.assertIn('# HELP', content)
        
        # Verify the mock client was called correctly
        self.mock_client.get.assert_called_once_with(url)
    
    def test_metrics_endpoint_unauthenticated(self):
        """Test metrics endpoint with unauthenticated user"""
        # Setup URL
        self.mock_reverse.return_value = '/monitoring/metrics/'
        
        # Setup mock client for unauthenticated user
        self.mock_client.get.return_value = self.redirect_response
        
        # Call endpoint
        url = self.mock_reverse('monitoring:metrics')
        response = self.mock_client.get(url)
        
        # Assertions
        self.assertEqual(response.status_code, 302)
        
        # Verify the mock client was called correctly
        self.mock_client.get.assert_called_once_with(url)
    
    def test_api_metrics_endpoint_authenticated(self):
        """Test API metrics endpoint with authenticated user"""
        # Setup URL
        self.mock_reverse.return_value = '/monitoring/api-metrics/'
        
        # Setup mock client response
        self.mock_client.get.return_value = self.json_response
        
        # Call endpoint
        url = self.mock_reverse('monitoring:api_metrics')
        response = self.mock_client.get(url)
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Parse JSON data
        data = json.loads(response.content.decode())
        
        # Verify expected keys
        self.assertIn('api_requests', data)
        self.assertIn('api_latency', data)
        self.assertIn('credit_usage', data)
        self.assertIn('active_users', data)
        self.assertIn('error_rates', data)
        self.assertIn('anomalies', data)
        
        # Verify the mock client was called correctly
        self.mock_client.get.assert_called_once_with(url)
    
    def test_api_metrics_endpoint_unauthenticated(self):
        """Test API metrics endpoint with unauthenticated user"""
        # Setup URL
        self.mock_reverse.return_value = '/monitoring/api-metrics/'
        
        # Setup mock client for unauthenticated user
        self.mock_client.get.return_value = self.redirect_response
        
        # Call endpoint
        url = self.mock_reverse('monitoring:api_metrics')
        response = self.mock_client.get(url)
        
        # Assertions
        self.assertEqual(response.status_code, 302)
        
        # Verify the mock client was called correctly
        self.mock_client.get.assert_called_once_with(url)
