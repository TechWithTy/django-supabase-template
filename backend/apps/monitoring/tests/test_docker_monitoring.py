import time
import random
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

User = get_user_model()


class UserBehaviorTrackingTests(TestCase):
    """Test class for user behavior tracking with Prometheus metrics"""
    
    def setUp(self):
        """Set up test user and client"""
        self.client = Client()
        self.username = 'testuser_behavior'
        self.password = 'secure_test_password'
        
        # Create test user
        self.user = User.objects.create_user(
            username=self.username,
            email='testuser_behavior@example.com',
            password=self.password
        )
    
    def test_api_request_tracking(self):
        """Test that API requests are tracked in Prometheus metrics"""
        # Login
        login_success = self.client.login(username=self.username, password=self.password)
        self.assertTrue(login_success, "Login failed")
        
        # Make API requests to generate metrics
        endpoints = [
            '/api/metrics/',
            '/api/users/profile/',
            '/api/non-existent/',  # To generate 404s
        ]
        
        for endpoint in endpoints:
            for _ in range(3):
                response = self.client.get(endpoint)
                print(f"Request to {endpoint}: {response.status_code}")
        
        # Check metrics endpoint
        response = self.client.get('/metrics/')
        self.assertEqual(response.status_code, 200, "Metrics endpoint not accessible")
        
        # Verify metrics are present in the response
        metrics_content = response.content.decode('utf-8')
        expected_metrics = [
            'api_requests_total',
            'api_request_latency_seconds',
        ]
        
        for metric in expected_metrics:
            self.assertIn(metric, metrics_content, f"Metric {metric} not found in response")


class AnomalyDetectionTests(TestCase):
    """Test class for API anomaly detection"""
    
    def setUp(self):
        """Set up test user and client"""
        self.client = Client()
        self.username = 'testuser_anomaly'
        self.password = 'secure_test_password'
        
        # Create test user
        self.user = User.objects.create_user(
            username=self.username,
            email='testuser_anomaly@example.com',
            password=self.password
        )
        
        # Login
        login_success = self.client.login(username=self.username, password=self.password)
        self.assertTrue(login_success, "Login failed")
    
    def test_error_anomaly_detection(self):
        """Test that error anomalies are detected"""
        # Generate error responses
        for _ in range(5):
            response = self.client.get('/api/non-existent-endpoint/')
            self.assertEqual(response.status_code, 404, "Expected 404 error")
        
        # Check metrics
        response = self.client.get('/metrics/')
        self.assertEqual(response.status_code, 200, "Metrics endpoint not accessible")
        
        # Look for anomaly metrics
        metrics_content = response.content.decode('utf-8')
        expected_metrics = [
            'api_error_rate',
            'anomaly_detection_triggered',
        ]
        
        for metric in expected_metrics:
            self.assertIn(metric, metrics_content, f"Metric {metric} not found in response")
    
    def test_high_latency_detection(self):
        """Test that high latency is detected"""
        # This is more of a placeholder test since we can't easily
        # force high latency in a test environment
        # Ideally, you would have a mock endpoint that artificially delays
        
        # Make some regular requests
        for _ in range(3):
            response = self.client.get('/api/users/profile/')
            self.assertEqual(response.status_code, 200, "Expected 200 response")
