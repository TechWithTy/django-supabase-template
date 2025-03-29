# Grafana Quickstart Guide

## Getting Grafana Running in Your Browser

This guide will walk you through the steps to get Grafana up and running with your Django Supabase Template application and access it in your browser.

## Step 1: Start the Monitoring Stack

Open your terminal and run the following command from the project root directory:

```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

This command starts Prometheus, Grafana, Node Exporter, and cAdvisor containers in detached mode.

## Step 2: Verify Containers are Running

Check that the containers are up and running:

```bash
docker-compose -f docker-compose.monitoring.yml ps
```

You should see something like:

```
    Name                   Command               State           Ports         
--------------------------------------------------------------------------------
grafana         /run.sh                          Up      0.0.0.0:3000->3000/tcp
prometheus      /bin/prometheus --config.f ...   Up      0.0.0.0:9090->9090/tcp
node-exporter   /bin/node_exporter --path. ...   Up      0.0.0.0:9100->9100/tcp
cadvisor        /usr/bin/cadvisor -logtost ...   Up      0.0.0.0:8080->8080/tcp
```

## Step 3: Open Grafana in Your Browser

1. Open your web browser
2. Navigate to [http://localhost:3000](http://localhost:3000)
3. You should see the Grafana login page

## Step 4: Log In to Grafana

1. Use the default credentials:
   - Username: `admin`
   - Password: `admin`

2. You'll be prompted to change your password - you can either set a new password or skip this step for development purposes by clicking "Skip".

## Step 5: Access the Pre-configured Dashboard

1. After logging in, click on the "Dashboards" icon in the left sidebar (four squares)
2. Click on "Browse"
3. Look for "Django API Monitoring" in the list and click on it
4. You should now see your dashboard with API metrics

## Troubleshooting

### Browser Can't Connect to Grafana

If you see "This site can't be reached" or "Connection refused" errors:

1. **Check if port 3000 is in use**:
   ```bash
   netstat -tuln | grep 3000
   ```
   If it's being used by another application, modify the port in docker-compose.monitoring.yml

2. **Check container logs**:
   ```bash
   docker-compose -f docker-compose.monitoring.yml logs grafana
   ```

3. **Restart the container**:
   ```bash
   docker-compose -f docker-compose.monitoring.yml restart grafana
   ```

### Dashboard Shows No Data

1. **Verify Prometheus is scraping your application**:
   - Open [http://localhost:9090/targets](http://localhost:9090/targets) in your browser
   - Check that the Django application target shows "UP" status

2. **Make sure your Django app is exposing metrics**:
   - Visit `/monitoring/metrics/` on your Django application 
   - You should see metrics in the Prometheus format

3. **Check Prometheus data source in Grafana**:
   - Go to Configuration → Data sources
   - Verify Prometheus is added with URL `http://prometheus:9090`
   - Click "Save & Test" to confirm connectivity

## Stopping the Monitoring Stack

When you're done, you can stop the monitoring stack with:

```bash
docker-compose -f docker-compose.monitoring.yml down
```

To remove all associated volumes (this will delete all collected data):

```bash
docker-compose -f docker-compose.monitoring.yml down -v
```

## Next Steps

Now that you have Grafana running:

1. Generate some traffic to your Django application to see metrics appear
2. Explore the different panels in the dashboard
3. Try using the time range selector at the top right to view different time periods
4. Refer to the [Grafana Complete Guide](./grafana_complete_guide.md) for more advanced usage
