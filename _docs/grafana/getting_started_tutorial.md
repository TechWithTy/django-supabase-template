# Getting Started with Grafana Monitoring

## Quick Tutorial to Run Grafana in Your Browser

### 1. Start the Monitoring Stack

From your project's root directory, run:

```bash
# Navigate to your project root if needed
cd c:\Users\tyriq\Documents\Github\django-supabase-template

# Start the monitoring services (Prometheus, Grafana, etc.)
docker-compose -f docker-compose.monitoring.yml up -d
```

### 2. Open Grafana in Your Browser

Once the services are running (which takes about 10-15 seconds), open your browser and navigate to:

**[http://localhost:3000](http://localhost:3000)**

### 3. Log In

Use the default credentials:
- Username: `admin`
- Password: `admin`

You'll be prompted to change your password on first login - you can skip this for development environments.

### 4. View the Dashboard

1. From the Grafana home screen, click on the menu icon (four squares) in the left sidebar
2. Select "Dashboards" > "Browse"
3. Click on "Django API Monitoring"

You'll now see your application metrics dashboard with panels for:
- API Request Rate
- API Latency
- Error Rate
- Anomaly Detection
- Credit Usage
- Active Users

### 5. Generate Some Data

To see metrics in action, make a few requests to your Django application endpoints:

```bash
# Example: Make some API requests using curl
curl http://localhost:8000/api/users/
curl http://localhost:8000/api/auth/login/
```

Refresh your Grafana dashboard to see real-time metrics appearing.

### Troubleshooting

**Problem**: Browser shows "Connection refused" when accessing Grafana

**Solution**: 
- Verify containers are running: `docker-compose -f docker-compose.monitoring.yml ps`
- Check Grafana logs: `docker-compose -f docker-compose.monitoring.yml logs grafana`
- Ensure port 3000 is not used by another service

**Problem**: Dashboard shows "No data" in panels

**Solution**:
- Make sure your Django app is running and exposing metrics
- Check Prometheus connection at Configuration > Data Sources 
- View raw metrics in Prometheus at [http://localhost:9090](http://localhost:9090)

### Stopping the Services

When you're done, you can stop the monitoring stack:

```bash
docker-compose -f docker-compose.monitoring.yml down
```

## What's Next?

- Explore the metrics in the Grafana interface
- Try creating custom dashboards
- Set up alerts for critical conditions
- Learn about the metrics collected in the [monitoring_setup.md](..\monitoring_setup.md) document
