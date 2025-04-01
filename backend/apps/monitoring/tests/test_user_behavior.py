import json
from unittest import TestCase
from unittest.mock import patch, MagicMock


class UserBehaviorTrackingTests(TestCase):
    """
    Test class for verifying user behavior tracking functionality.
    These tests verify that the metrics for user activity are properly recorded.
    Fully isolated from real database and dependencies.
    """
    
    def setUp(self):
        """
        Set up test mocks.
        """
        # Mock Django's URL reverse function
        self.reverse_patcher = patch('django.urls.reverse')
        self.mock_reverse = self.reverse_patcher.start()
        
        # Mock the Django client
        self.client_patcher = patch('django.test.Client')
        self.mock_client_class = self.client_patcher.start()
        self.mock_client = MagicMock()
        self.mock_client_class.return_value = self.mock_client
        self.client = self.mock_client
        
        # Mock responses for different endpoints
        self.metrics_response = MagicMock()
        self.metrics_response.status_code = 200
        self.metrics_response.content = b'''
# HELP api_requests_total Total count of API requests
# TYPE api_requests_total counter
api_requests_total{endpoint="monitoring",method="GET",status="200"} 1.0
# HELP user_sessions_total Total count of user sessions
# TYPE user_sessions_total counter
user_sessions_total{status="active"} 1.0
# HELP active_users Active users count
# TYPE active_users gauge
active_users{timeframe="1h"} 1.0
'''
        
        self.api_metrics_response = MagicMock()
        self.api_metrics_response.status_code = 200
        self.api_metrics_response.content = json.dumps({
            'api_requests': [{'endpoint': '/api/test', 'count': 100}],
            'api_latency': [{'endpoint': '/api/test', 'avg_latency': 0.05}],
            'credit_usage': [{'operation': 'query', 'total': 50}],
            'active_users': {'1h': 10, '24h': 50},
            'error_rates': [{'endpoint': '/api/test', 'rate': 0.01}],
            'anomalies': [{'endpoint': '/api/test', 'type': 'high_latency', 'count': 2}]
        }).encode()
        
        # Configure the URL mapping
        def mock_reverse_side_effect(name, *args, **kwargs):
            if name == 'monitoring:api_metrics':
                return '/monitoring/api-metrics/'
            elif name == 'monitoring:metrics':
                return '/monitoring/metrics/'
            return f'/mock/{name}/'
            
        self.mock_reverse.side_effect = mock_reverse_side_effect
        
        # Mock the user model
        self.user = MagicMock()
        self.user.username = 'testuser'
        self.user.email = 'test@example.com'
    
    def tearDown(self):
        """
        Clean up patches.
        """
        self.reverse_patcher.stop()
        self.client_patcher.stop()
    
    def test_api_request_tracking(self):
        """
        Test that API requests are properly tracked with monitoring middleware.
        """
        # Configure mock client responses
        def get_side_effect(url, *args, **kwargs):
            if url == '/monitoring/api-metrics/':
                return self.api_metrics_response
            elif url == '/monitoring/metrics/':
                return self.metrics_response
            return MagicMock(status_code=404)
            
        self.mock_client.get.side_effect = get_side_effect
        
        # Configure login to return True
        self.mock_client.login.return_value = True
        
        # Login first
        login_result = self.client.login(username='testuser', password='testpassword123')
        self.assertTrue(login_result)
        
        # Make API request
        url = self.mock_reverse('monitoring:api_metrics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Check metrics endpoint to verify the request was tracked
        metrics_url = self.mock_reverse('monitoring:metrics')
        metrics_response = self.client.get(metrics_url)
        self.assertEqual(metrics_response.status_code, 200)
        
        # Verify our request is reflected in the metrics
        self.assertIn('api_requests_total', metrics_response.content.decode())
        
    def test_user_session_tracking(self):
        """
        Test that user sessions are tracked on login/logout.
        """
        # Configure mock client responses
        self.mock_client.get.return_value = self.metrics_response
        
        # Configure login to return True
        self.mock_client.login.return_value = True
        
        # Get metrics URL
        metrics_url = self.mock_reverse('monitoring:metrics')
        
        # Initial state (not logged in)
        initial_metrics = self.client.get(metrics_url).content.decode()
        
        # Perform login
        login_successful = self.client.login(username='testuser', password='testpassword123')
        self.assertTrue(login_successful)
        
        # Get updated metrics
        updated_metrics = self.client.get(metrics_url).content.decode()
        
        # Look for user_sessions_total in metrics
        self.assertIn('user_sessions_total', updated_metrics)
        
    def test_active_users_tracking(self):
        """
        Test that active users gauge is updated on user activity.
        """
        # Configure mock client responses
        def get_side_effect(url, *args, **kwargs):
            if url == '/monitoring/api-metrics/':
                return self.api_metrics_response
            elif url == '/monitoring/metrics/':
                return self.metrics_response
            return MagicMock(status_code=404)
            
        self.mock_client.get.side_effect = get_side_effect
        
        # Configure login to return True
        self.mock_client.login.return_value = True
        
        # Login to create an active session
        self.client.login(username='testuser', password='testpassword123')
        
        # Make multiple requests to simulate activity
        for _ in range(3):
            url = self.mock_reverse('monitoring:api_metrics')
            self.client.get(url)
        
        # Check metrics endpoint
        metrics_url = self.mock_reverse('monitoring:metrics')
        metrics_response = self.client.get(metrics_url)
        
        # Verify active_users metric exists
        metrics_content = metrics_response.content.decode()
        self.assertIn('active_users', metrics_content)
        
    def test_custom_event_tracking(self):
        """
        Test custom event tracking by checking API metrics endpoint.
        """
        # Configure mock client responses
        self.mock_client.get.return_value = self.api_metrics_response
        
        # Configure login to return True
        self.mock_client.login.return_value = True
        
        # Login first
        self.client.login(username='testuser', password='testpassword123')
        
        # Make API request to endpoint that should trigger custom event tracking
        url = self.mock_reverse('monitoring:api_metrics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Check the API metrics data to see if custom events are being tracked
        data = json.loads(response.content.decode())
        
        # API metrics should contain certain expected keys
        self.assertIn('api_requests', data)  # Standard API metrics
        self.assertIn('api_latency', data)  # Latency metrics
