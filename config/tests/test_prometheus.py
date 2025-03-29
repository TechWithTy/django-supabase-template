import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

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
        
        # Add a small delay between requests
        time.sleep(0.5)
    
    # Now try to get the metrics
    print("\nFetching Prometheus metrics...")
    response = client.get('/metrics/', follow=True)
    
    if response.status_code == 200:
        print("\nSuccess! Prometheus metrics endpoint is working.")
        print("\nSample metrics (first 20 lines):")
        # Print first 20 lines of metrics for preview
        metrics_lines = response.content.decode('utf-8').split('\n')
        for line in metrics_lines[:20]:
            if line.strip() and not line.startswith('#'):
                print(line)
    else:
        print(f"\nError accessing metrics: Status code {response.status_code}")
        print(f"Response content: {response.content[:500]}")

if __name__ == '__main__':
    test_prometheus_metrics()
