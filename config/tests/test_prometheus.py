import os
import sys

# Add the project root to Python path first
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now add the backend directory to the path
backend_dir = os.path.join(project_root, 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Set correct Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.core.settings')

import django
django.setup()

from django.test import Client
import time

def test_prometheus_metrics():
    """
    Test function to generate some metrics for Prometheus by making API requests.
    """
    # Use localhost as the server name and follow redirects
    client = Client(SERVER_NAME='localhost', follow=True)
    
    print("Making test requests to generate metrics...")
    # Make several requests to different endpoints to generate metrics
    for _ in range(3):
        # Try accessing the admin page (with trailing slash)
        response = client.get('/admin/', follow=True)
        print(f"Admin request status: {response.status_code}")
        
        # Try accessing a non-existent page to generate 404 metrics
        response = client.get('/non-existent-page/', follow=True)
        print(f"404 request status: {response.status_code}")
        
        # Try accessing the metrics endpoint
        response = client.get('/metrics/', follow=True)
        print(f"Metrics request status: {response.status_code}")
    
    # Now verify metrics were collected by checking the /metrics endpoint
    metrics_response = client.get('/metrics/')
    metrics_content = metrics_response.content.decode('utf-8')
    
    print("\n===== PROMETHEUS METRICS VERIFICATION =====")
    print(f"Metrics endpoint status: {metrics_response.status_code}")
    
    # Check that the response is successful
    assert metrics_response.status_code == 200, "Metrics endpoint returned non-200 status code"
    
    # Check for expected metric types in the response
    expected_metrics = [
        'django_http_requests_total',
        'django_http_responses_total_by_status',
        'django_http_requests_latency_seconds',
    ]
    
    success = True
    for metric in expected_metrics:
        if metric in metrics_content:
            print(f" Found metric: {metric}")
        else:
            print(f" Missing metric: {metric}")
            success = False
    
    # Check for our specific test patterns
    test_patterns = [
        'path="/admin/"',
        'path="/non-existent-page/"',
        'path="/metrics/"',
        'status="404"',
    ]
    
    print("\n----- Request Pattern Checks -----")
    for pattern in test_patterns:
        if pattern in metrics_content:
            print(f" Found test pattern: {pattern}")
        else:
            # Try partial matching for path patterns as implementations may vary
            if 'path=' in pattern and any(p in metrics_content for p in [pattern.replace('"', "'"), pattern.split('=')[1]]):
                print(f" Found similar pattern to: {pattern} (format may differ)")
            else:
                print(f" Missing test pattern: {pattern}")
    
    # Print some actual metrics for verification
    print("\n----- Sample Metrics (first 5) -----")
    metric_lines = [line for line in metrics_content.split('\n') 
                   if line.strip() and not line.startswith('#')]
    for line in metric_lines[:5]:
        print(line)
    
    print("\n===== PROMETHEUS INTEGRATION STATUS =====")
    if success:
        print(" PROMETHEUS METRICS COLLECTION WORKING PROPERLY")
    else:
        print(" SOME EXPECTED PROMETHEUS METRICS ARE MISSING")
        
    assert success, "Some expected Prometheus metrics are missing!"

if __name__ == '__main__':
    test_prometheus_metrics()
