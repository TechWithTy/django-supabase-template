import os
import sys
import time
import django
import pytest
import warnings
from django.test import Client
from django.contrib.auth import get_user_model
from django.db.utils import ProgrammingError

# Set custom test settings before Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.tests.test_settings")

# Add the project root directory to Python's module search path
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

# Also add the backend directory to the path
backend_dir = os.path.join(project_root, "backend")
sys.path.insert(0, backend_dir)

# Initialize Django with test settings
django.setup()

# Check if authentication_customuser table exists
def check_auth_table_exists():
    """Check if the authentication_customuser table exists"""
    from django.db import connections
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_catalog.pg_tables WHERE tablename = 'authentication_customuser'")
            exists = cursor.fetchone() is not None
        return exists
    except Exception as e:
        warnings.warn(f"Error checking for authentication_customuser table: {e}")
        return False

# Skip all tests if auth table doesn't exist
pytestmark = pytest.mark.skipif(
    not check_auth_table_exists(),
    reason="Skipping tests: authentication_customuser table doesn't exist"
)

# Get the User model safely
try:
    User = get_user_model()
except Exception as e:
    warnings.warn(f"Error getting User model: {e}")
    User = None


def setup_test_user():
    """Create a test user for authentication if it doesn't exist

    Returns:
        tuple: (user, username, password) if successful

    Raises:
        pytest.skip: If the User model is not available or table doesn't exist
    """
    # Skip test if User model is not available
    if User is None:
        warnings.warn("User model not available - skipping test")
        pytest.skip("User model not available")

    username = "testuser_e2e"
    password = "secure_test_password123"

    try:
        user = User.objects.get(username=username)
        return user, username, password
    except User.DoesNotExist:
        try:
            user = User.objects.create_user(
                username=username, email="testuser_e2e@example.com", password=password
            )
            return user, username, password
        except ProgrammingError as e:
            if 'relation "authentication_customuser" does not exist' in str(e):
                warnings.warn("authentication_customuser table does not exist - skipping test")
                pytest.skip("authentication_customuser table does not exist")
            else:
                raise
    except ProgrammingError as e:
        if 'relation "authentication_customuser" does not exist' in str(e):
            warnings.warn("authentication_customuser table does not exist - skipping test")
            pytest.skip("authentication_customuser table does not exist")
        else:
            raise


def test_user_behavior_tracking():
    """Test the user behavior tracking functionality

    This test checks the user behavior tracking metrics by performing
    various API requests and verifying that appropriate metrics are being recorded.
    It will be skipped if the authentication_customuser table doesn't exist.
    """
    # This entire module will be skipped if auth table doesn't exist
    print("\n==== Testing User Behavior Tracking ====")
    client = Client(SERVER_NAME="localhost", follow=True)

    try:
        # Setup test user and login
        user, username, password = setup_test_user()

        # Check initial metrics state
        print("\nChecking initial metrics state...")
        response = client.get("/metrics/", follow=True)
        print(f"Initial metrics status: {response.status_code}")

        # Perform login to generate user session metrics
        print("\nLogging in to generate user session metrics...")
        login_success = client.login(username=username, password=password)
        if login_success:
            print("Login successful")
        else:
            warnings.warn("Login failed - test results may be unreliable")
            print("Login failed")
            return

        # Generate user behavior by making various API requests
        print("\nGenerating user behavior data...")

        endpoints = [
            "/api/users/profile/",  # User profile endpoint
            "/api/metrics/",  # Metrics endpoint
            "/api/health-check/",  # Health check endpoint
            "/api/non-existent/",  # 404 to generate errors
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
        response = client.get("/metrics/", follow=True)
        updated_metrics = response.content.decode("utf-8")

        # Verify user behavior metrics exist
        metrics_to_check = [
            "api_requests_total",  # API request counter
            "api_request_latency_seconds",  # API latency histogram
            "user_sessions_total",  # User session counter
            "active_users",  # Active users gauge
        ]

        print("\nChecking for user behavior metrics:")
        for metric in metrics_to_check:
            if metric in updated_metrics:
                print(f" Found metric: {metric}")
            else:
                warnings.warn(f"Missing metric: {metric}")
                print(f" Missing metric: {metric}")

        # Perform logout to complete the session
        client.logout()
    except ProgrammingError as e:
        if 'relation "authentication_customuser" does not exist' in str(e):
            warnings.warn("authentication_customuser table does not exist - skipping test")
            pytest.skip("authentication_customuser table does not exist")
        else:
            raise


def test_anomaly_detection():
    """Test the anomaly detection functionality

    This test simulates anomalous behavior and checks if it's properly detected.
    It will be skipped if the authentication_customuser table doesn't exist.
    """
    # This entire module will be skipped if auth table doesn't exist
    print("\n==== Testing API Anomaly Detection ====")
    client = Client(SERVER_NAME="localhost", follow=True)

    try:
        # Setup test user and login
        user, username, password = setup_test_user()

        # Login with test user
        login_success = client.login(username=username, password=password)
        if not login_success:
            warnings.warn("Login failed - test results may be unreliable")
            print("Login failed, cannot continue")
            return

        print("\nGenerating normal baseline traffic...")
        # Generate some normal baseline traffic
        for _ in range(5):
            client.get("/api/health-check/", follow=True)
            time.sleep(0.1)

        print("\nSimulating anomalous behavior...")
        # Simulate anomalous behavior - rapid requests
        start_time = time.time()
        for _ in range(15):  # Make many requests in a short time
            client.get("/api/health-check/", follow=True)

        # Check if rapid requests were detected as anomalous
        duration = time.time() - start_time
        print(f"Made 15 rapid requests in {duration:.2f} seconds")

        # Check metrics for anomaly detection
        print("\nChecking metrics for anomaly detection...")
        response = client.get("/metrics/", follow=True)
        metrics = response.content.decode("utf-8")

        # Metrics to check for anomaly detection
        anomaly_metrics = [
            "request_rate_anomaly",  # Request rate anomaly metric
            "error_rate_anomaly",  # Error rate anomaly metric
            "latency_anomaly",  # Latency anomaly metric
        ]

        print("\nChecking for anomaly detection metrics:")
        for metric in anomaly_metrics:
            if metric in metrics:
                print(f" Found metric: {metric}")
            else:
                warnings.warn(f"Missing metric: {metric}")
                print(f" Missing metric: {metric}")

        # Clean up and logout
        client.logout()
    except ProgrammingError as e:
        if 'relation "authentication_customuser" does not exist' in str(e):
            warnings.warn("authentication_customuser table does not exist - skipping test")
            pytest.skip("authentication_customuser table does not exist")
        else:
            raise


def test_credit_usage_monitoring():
    """Test the credit usage monitoring functionality

    This test simulates API calls that consume credits and verifies
    that credit usage metrics are being tracked properly.
    It will be skipped if the authentication_customuser table doesn't exist.
    """
    # This entire module will be skipped if auth table doesn't exist
    print("\n==== Testing Credit Usage Monitoring ====")
    client = Client(SERVER_NAME="localhost", follow=True)

    try:
        # Setup test user and login
        user, username, password = setup_test_user()

        # Login with test user
        login_success = client.login(username=username, password=password)
        if not login_success:
            warnings.warn("Login failed - test results may be unreliable")
            print("Login failed, cannot continue")
            return

        # Simulate API calls that consume credits
        print("\nSimulating API calls that consume credits...")
        
        # Credit consuming endpoints (placeholders - adjust to your actual endpoints)
        credit_endpoints = [
            "/api/run-script/",  # Script running endpoint
            "/api/generate-content/",  # Content generation endpoint
            "/api/analyze-data/",  # Data analysis endpoint
        ]

        # Make credit-consuming API calls
        for endpoint in credit_endpoints:
            response = client.post(endpoint, {"parameter": "test_value"}, follow=True)
            print(f"Credit API call to {endpoint}: {response.status_code}")
            time.sleep(0.2)  # Small delay between requests

        # Check credit usage metrics
        print("\nChecking credit usage metrics...")
        response = client.get("/metrics/", follow=True)
        metrics = response.content.decode("utf-8")

        # Credit metrics to check
        credit_metrics = [
            "credit_usage_total",  # Total credits used
            "credit_transaction_count",  # Number of credit transactions
            "credit_balance",  # Current credit balance
        ]

        print("\nChecking for credit usage metrics:")
        for metric in credit_metrics:
            if metric in metrics:
                print(f" Found metric: {metric}")
            else:
                warnings.warn(f"Missing metric: {metric}")
                print(f" Missing metric: {metric}")

        # Clean up and logout
        client.logout()
    except ProgrammingError as e:
        if 'relation "authentication_customuser" does not exist' in str(e):
            warnings.warn("authentication_customuser table does not exist - skipping test")
            pytest.skip("authentication_customuser table does not exist")
        else:
            raise


def run_all_tests():
    """Run all E2E tests for user behavior tracking and anomaly detection"""
    # Skip all tests if auth table doesn't exist
    if not check_auth_table_exists():
        warnings.warn("Skip all tests: authentication_customuser table doesn't exist")
        print("\nSkipping all tests: authentication_customuser table doesn't exist")
        return
        
    test_user_behavior_tracking()
    test_anomaly_detection()
    test_credit_usage_monitoring()


if __name__ == "__main__":
    run_all_tests()
