import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class MetricsEndpointsTests(TestCase):
    """
    Test class for verifying the Prometheus metrics endpoints are working correctly.
    """
    
    def setUp(self):
        """
        Set up test data including a test user for authenticated requests.
        """
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        self.client.login(username='testuser', password='testpassword123')
    
    def test_metrics_endpoint_authenticated(self):
        """
        Test that the metrics endpoint returns 200 for authenticated users.
        """
        url = reverse('monitoring:metrics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain; version=0.0.4; charset=utf-8')
        
        # Verify that the response contains Prometheus metrics
        self.assertIn('# HELP', response.content.decode())
    
    def test_metrics_endpoint_unauthenticated(self):
        """
        Test that the metrics endpoint requires authentication.
        """
        self.client.logout()
        url = reverse('monitoring:metrics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirects to login page
    
    def test_api_metrics_endpoint_authenticated(self):
        """
        Test that the API metrics endpoint returns valid JSON for authenticated users.
        """
        url = reverse('monitoring:api_metrics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Verify that the response is valid JSON and has expected keys
        data = json.loads(response.content.decode())
        self.assertIn('api_requests', data)
        self.assertIn('api_latency', data)
        self.assertIn('credit_usage', data)
        self.assertIn('active_users', data)
        self.assertIn('error_rates', data)
        self.assertIn('anomalies', data)
    
    def test_api_metrics_endpoint_unauthenticated(self):
        """
        Test that the API metrics endpoint requires authentication.
        """
        self.client.logout()
        url = reverse('monitoring:api_metrics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirects to login page
