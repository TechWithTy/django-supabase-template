# Grafana Complete Guide for Django-Supabase Template

## Overview

This comprehensive guide explains how to set up, access, and use Grafana for monitoring your Django application. Grafana provides powerful visualization and alerting capabilities that help you understand your application's performance and health.

## Architecture

The monitoring stack consists of the following components:

1. **Django Monitoring App**: Collects and exposes custom metrics from your application
2. **Prometheus**: Scrapes and stores metrics from your Django application
3. **Grafana**: Visualizes metrics with interactive dashboards
4. **Node Exporter**: Collects system-level metrics (CPU, memory, disk, network)
5. **cAdvisor**: Collects container-level metrics from Docker

## Prerequisites

- Docker and Docker Compose installed
- Django-Prometheus package (already included in requirements.txt)
- Port 3000 available for Grafana web interface
- Port 9090 available for Prometheus web interface
- Port 9100 available for Node Exporter
- Port 8080 available for cAdvisor

## Quick Start

### 1. Starting the Monitoring Stack

To run only the monitoring components (Prometheus and Grafana):

```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

To run the entire stack including your Django application with monitoring:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 2. Accessing Grafana in Your Browser

Once the containers are running, Grafana will be available at:

**http://localhost:3000**

You will see the Grafana login screen when you access this URL in your browser.

### 3. Logging In

The default credentials are:
- **Username**: `admin`
- **Password**: `admin`

You will be prompted to change the password on first login (recommended for security).

### 4. Navigating the Interface

After logging in, you'll see the Grafana home dashboard. The main navigation elements are:

- **Left sidebar**: Access to dashboards, explore, alerting, and configuration
- **Top bar**: Search, create, dashboard settings, and user preferences

## Available Dashboards

The template includes several pre-configured dashboards:

### 1. Django API Monitoring

Provides a comprehensive view of your API's performance with panels for:

- **API Request Rate**: Requests per second by endpoint
- **API Latency**: 95th percentile response times
- **Error Rate**: Percentage of requests resulting in 5xx errors
- **Anomaly Detection**: Unusual patterns in API usage
- **Credit Usage**: Rate of credit consumption by operation
- **Active Users**: Count of active users over time

To access this dashboard:
1. Click the "Dashboards" icon in the left sidebar
2. Select "Browse" 
3. Click on "Django API Monitoring"

### 2. System Overview

Monitors the infrastructure running your application with panels for:

- CPU, memory, and disk usage
- Network traffic
- Container resource utilization

## Adding the Prometheus Data Source (If Not Auto-Configured)

If the Prometheus data source isn't automatically configured, you can add it manually:

1. Click on the gear icon (⚙️) in the left sidebar to open the Configuration menu
2. Select "Data sources"
3. Click "Add data source"
4. Select "Prometheus" from the list
5. Set the URL to `http://prometheus:9090` (when using Docker Compose) or `http://localhost:9090` (when accessing from outside)
6. Click "Save & Test" to verify the connection

## Using the Dashboards

### Filtering and Time Range Selection

You can customize your view in any dashboard by:

1. **Time Range Selection**: Use the time picker in the top-right corner to select a specific period (last 5 minutes to 5 years, or custom)
2. **Refresh Rate**: Set the auto-refresh interval or manually refresh
3. **Variables**: Some dashboards include dropdown filters to focus on specific endpoints, services, etc.

### Exploring Metrics

To explore raw metrics:

1. Click the "Explore" icon in the left sidebar
2. Select "Prometheus" as your data source
3. Start typing a metric name to get auto-completion suggestions
4. Use PromQL queries to filter and analyze data

Example PromQL queries:
```
# Request rate by endpoint
sum(rate(api_requests_total[5m])) by (endpoint)

# Error rate
100 * (rate(api_requests_total{status=~"5.."}[5m]) / rate(api_requests_total[5m]))

# 95th percentile latency
histogram_quantile(0.95, sum(rate(api_request_latency_seconds_bucket[5m])) by (le, endpoint))
```

## Setting Up Alerts

To create alerts based on your metrics:

1. Navigate to the panel you want to create an alert for
2. Click on the panel title and select "Edit"
3. Click the "Alert" tab
4. Configure the alert conditions, evaluation frequency, and notifications
5. Click "Save" to activate the alert

## Troubleshooting Browser Access

### Grafana Isn't Loading in Browser

1. **Verify services are running**:
   ```bash
   docker-compose -f docker-compose.monitoring.yml ps
   ```
   Confirm that the Grafana container shows as "Up".

2. **Check port availability**:
   ```bash
   netstat -tuln | grep 3000
   ```
   If you see another service using port 3000, you'll need to modify the port mapping in docker-compose.yml.

3. **Check container logs**:
   ```bash
   docker-compose -f docker-compose.monitoring.yml logs grafana
   ```
   Look for error messages that might indicate configuration problems.

### Error "Could not connect to Prometheus"

1. Check if Prometheus is running:
   ```bash
   docker-compose -f docker-compose.monitoring.yml ps prometheus
   ```

2. Verify Prometheus is accessible by visiting http://localhost:9090 in your browser

3. Check the data source configuration in Grafana:
   - Go to Configuration → Data sources
   - Edit the Prometheus data source
   - Make sure the URL is correct (`http://prometheus:9090` for Docker Compose networking)
   - Click "Save & Test" to verify the connection

## Extending the Monitoring System

### Adding Custom Metrics to Your Django App

Define new metrics in your Django application:

```python
from prometheus_client import Counter, Histogram, Gauge

# Define a new counter
MY_NEW_COUNTER = Counter(
    'my_new_metric_total',
    'Description of my new metric',
    ['label1', 'label2']
)

# Increment the counter in your code
MY_NEW_COUNTER.labels(label1='value1', label2='value2').inc()
```

### Creating Custom Dashboards

1. Click "+ Create" in the sidebar and select "Dashboard"
2. Click "Add new panel"
3. Configure the visualization type, metrics query, and display options
4. Save the panel and the dashboard

Alternatively, you can create JSON dashboard definitions and place them in `config/grafana/provisioning/dashboards/`.

## Security Best Practices

1. **Change Default Credentials**: Immediately change the default admin password
2. **Use Environment Variables**: Store sensitive configuration in environment variables
3. **Configure Authentication**: For production, consider setting up LDAP, OAuth, or other advanced authentication
4. **Restrict Access**: Use the Django authentication for `/metrics` endpoint to prevent unauthorized access

## Resources

- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/introduction/overview/)
- [PromQL Query Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)
- [Django-Prometheus](https://github.com/korfuri/django-prometheus)
