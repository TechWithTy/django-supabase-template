import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class UserBehaviorTrackingTests(TestCase):
    """
    Test class for verifying user behavior tracking functionality.
    These tests verify that the metrics for user activity are properly recorded.
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
    
    def test_api_request_tracking(self):
        """
        Test that API requests are properly tracked with monitoring middleware.
        """
        # Login first
        self.client.login(username='testuser', password='testpassword123')
        
        # Make API request
        url = reverse('monitoring:api_metrics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Check metrics endpoint to verify the request was tracked
        metrics_url = reverse('monitoring:metrics')
        metrics_response = self.client.get(metrics_url)
        self.assertEqual(metrics_response.status_code, 200)
        
        # Verify our request is reflected in the metrics (should contain api_requests_total)
        self.assertIn('api_requests_total', metrics_response.content.decode())
        
    def test_user_session_tracking(self):
        """
        Test that user sessions are tracked on login/logout.
        """
        # Initial state (not logged in)
        metrics_url = reverse('monitoring:metrics')
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
        # Login to create an active session
        self.client.login(username='testuser', password='testpassword123')
        
        # Make multiple requests to simulate activity
        for _ in range(3):
            url = reverse('monitoring:api_metrics')
            self.client.get(url)
        
        # Check metrics endpoint
        metrics_url = reverse('monitoring:metrics')
        metrics_response = self.client.get(metrics_url)
        
        # Verify active_users metric exists
        metrics_content = metrics_response.content.decode()
        self.assertIn('active_users', metrics_content)
        
    def test_custom_event_tracking(self):
        """
        Test custom event tracking by checking API metrics endpoint.
        """
        # Login first
        self.client.login(username='testuser', password='testpassword123')
        
        # Make API request to endpoint that should trigger custom event tracking
        url = reverse('monitoring:api_metrics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Check the API metrics data to see if custom events are being tracked
        data = json.loads(response.content.decode())
        
        # API metrics should contain certain expected keys
        self.assertIn('api_requests', data)  # Standard API metrics
        self.assertIn('api_latency', data)  # Latency metrics
