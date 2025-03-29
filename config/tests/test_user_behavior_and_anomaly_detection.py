import os
import sys
import time
import random
import django
from django.test import Client
from django.contrib.auth import get_user_model

# Add the project root directory to Python's module search path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Also add the backend directory to the path
backend_dir = os.path.join(project_root, 'backend')
sys.path.insert(0, backend_dir)

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Initialize Django
django.setup()

User = get_user_model()


def setup_test_user():
    """Create a test user for authentication if it doesn't exist"""
    username = 'testuser_e2e'
    password = 'secure_test_password123'
    
    try:
        user = User.objects.get(username=username)
        print(f"Using existing test user: {username}")
        return user, username, password
    except User.DoesNotExist:
        user = User.objects.create_user(
            username=username,
            email='testuser_e2e@example.com',
            password=password
        )
        print(f"Created new test user: {username}")
        return user, username, password


def test_user_behavior_tracking():
    """Test the user behavior tracking functionality"""
    print("\n==== Testing User Behavior Tracking ====")
    client = Client(SERVER_NAME='localhost', follow=True)
    
    # Setup test user and login
    user, username, password = setup_test_user()
    
    # Check initial metrics state
    print("\nChecking initial metrics state...")
    response = client.get('/metrics/', follow=True)
    print(f"Initial metrics status: {response.status_code}")
    
    # Perform login to generate user session metrics
    print("\nLogging in to generate user session metrics...")
    login_success = client.login(username=username, password=password)
    if login_success:
        print("Login successful")
    else:
        print("Login failed")
        return
    
    # Generate user behavior by making various API requests
    print("\nGenerating user behavior data...")
    
    endpoints = [
        '/api/users/profile/',      # User profile endpoint
        '/api/metrics/',            # Metrics endpoint
        '/api/health-check/',       # Health check endpoint
        '/api/non-existent/',       # 404 to generate errors
    ]
    
    # Make requests to generate metrics
    for endpoint in endpoints:
        for _ in range(3):
            response = client.get(endpoint, follow=True)
            print(f"Request to {endpoint}: {response.status_code}")
            # Add a small delay between requests
            time.sleep(0.2)
    
    # Check updated metrics
    print("\nChecking updated metrics...")
    response = client.get('/metrics/', follow=True)
    updated_metrics = response.content.decode('utf-8')
    
    # Verify user behavior metrics exist
    metrics_to_check = [
        'api_requests_total',            # API request counter
        'api_request_latency_seconds',   # API latency histogram
        'user_sessions_total',           # User session counter
        'active_users'                   # Active users gauge
    ]
    
    print("\nChecking for user behavior metrics:")
    for metric in metrics_to_check:
        if metric in updated_metrics:
            print(f"u2713 Found metric: {metric}")
        else:
            print(f"u2717 Missing metric: {metric}")
    
    # Perform logout to complete the session
    client.logout()


def test_anomaly_detection():
    """Test the anomaly detection functionality"""
    print("\n==== Testing API Anomaly Detection ====")
    client = Client(SERVER_NAME='localhost', follow=True)
    
    # Setup test user and login
    user, username, password = setup_test_user()
    login_success = client.login(username=username, password=password)
    if not login_success:
        print("Login failed, skipping anomaly detection tests")
        return
    
    # Check initial anomaly metrics
    print("\nChecking initial anomaly metrics...")
    response = client.get('/metrics/', follow=True)
    print(f"Initial metrics status: {response.status_code}")
    
    # Generate anomalies: server errors, high latency, error rate spikes
    print("\nGenerating server error anomalies...")
    for _ in range(5):
        # Request to endpoints that will generate 404s and 500s
        response = client.get('/api/forced-error/', follow=True)
        print(f"Forced error request: {response.status_code}")
        time.sleep(0.1)
    
    print("\nGenerating high latency anomalies...")
    for _ in range(3):
        # Use an endpoint that simulates high latency
        # Ideally, this would be a real endpoint that's slow, but we're simulating
        response = client.get('/api/slow-endpoint/?delay=1', follow=True)
        print(f"Slow endpoint request: {response.status_code}")
    
    print("\nGenerating rapid requests for rate-based anomalies...")
    for _ in range(10):
        # Make rapid requests to simulate suspicious activity
        response = client.get('/api/users/profile/', follow=True)
    
    # Check updated anomaly metrics
    print("\nChecking updated anomaly metrics...")
    response = client.get('/metrics/', follow=True)
    updated_metrics = response.content.decode('utf-8')
    
    # Verify anomaly detection metrics exist
    anomaly_metrics = [
        'api_error_rate',                    # API error rate
        'anomaly_detection_triggered_total', # Anomaly counter
        'api_response_time_threshold'        # Response time threshold
    ]
    
    print("\nChecking for anomaly detection metrics:")
    for metric in anomaly_metrics:
        if metric in updated_metrics:
            print(f"u2713 Found metric: {metric}")
        else:
            print(f"u2717 Missing metric: {metric}")
    
    # Logout to complete the session
    client.logout()


def test_credit_usage_monitoring():
    """Test the monitoring of credit usage in credit-based operations"""
    print("\n==== Testing Credit Usage Monitoring ====")
    client = Client(SERVER_NAME='localhost', follow=True)
    
    # Setup test user and login
    user, username, password = setup_test_user()
    login_success = client.login(username=username, password=password)
    if not login_success:
        print("Login failed, skipping credit usage monitoring tests")
        return
    
    # Check initial credit metrics
    print("\nChecking initial credit usage metrics...")
    response = client.get('/metrics/', follow=True)
    print(f"Initial metrics status: {response.status_code}")
    
    # Make requests to credit-based endpoints
    credit_operations = [
        '/api/credits/use-credits/',    # Simulate a credit-using operation
        '/api/features/premium/'         # Simulate premium feature access
    ]
    
    print("\nMaking requests to credit-based endpoints...")
    for endpoint in credit_operations:
        for _ in range(2):
            # You may need to customize payload based on actual API
            payload = {'credits': random.randint(1, 5), 'operation': 'test_operation'}
            response = client.post(endpoint, data=payload, follow=True)
            print(f"Credit operation request to {endpoint}: {response.status_code}")
            time.sleep(0.2)
    
    # Check updated credit metrics
    print("\nChecking updated credit usage metrics...")
    response = client.get('/metrics/', follow=True)
    updated_metrics = response.content.decode('utf-8')
    
    # Verify credit monitoring metrics exist
    credit_metrics = [
        'credit_usage_total',               # Credit usage counter
        'credit_operation_latency_seconds'  # Credit operation latency
    ]
    
    print("\nChecking for credit usage metrics:")
    for metric in credit_metrics:
        if metric in updated_metrics:
            print(f"u2713 Found metric: {metric}")
        else:
            print(f"u2717 Missing metric: {metric}")
    
    # Logout to complete the session
    client.logout()


def run_all_tests():
    """Run all E2E tests for user behavior tracking and anomaly detection"""
    print("Starting E2E tests for user behavior tracking and anomaly detection...")
    test_user_behavior_tracking()
    test_anomaly_detection()
    test_credit_usage_monitoring()
    print("\nAll tests completed!")


if __name__ == '__main__':
    run_all_tests()
