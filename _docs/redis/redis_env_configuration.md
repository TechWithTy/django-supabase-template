# Redis and Grafana Environment Configuration

This document provides the recommended environment variables for Redis and Grafana configuration.

## Redis Configuration

```env
# Redis Configuration
REDIS_PASSWORD=your_secure_redis_password
REDIS_PORT=6379
REDIS_DB=0
REDIS_DATABASES=16  # Total number of available Redis databases
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:${REDIS_PORT}/${REDIS_DB}

# Celery Configuration (Updated with Redis Auth)
CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:${REDIS_PORT}/${REDIS_DB}
CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@redis:${REDIS_PORT}/${REDIS_DB}
```

## Grafana Configuration 

```env
# Grafana Configuration
GRAFANA_USERNAME=admin
GRAFANA_PASSWORD=secure_grafana_password
GRAFANA_PORT=3000

# Prometheus Configuration
PROMETHEUS_PORT=9090
```

## Testing Configuration

For CI/CD testing environments, these default values are used if not explicitly provided:

```env
REDIS_PASSWORD=redis_default_password_for_ci
REDIS_PORT=6379
REDIS_DB=0
REDIS_DATABASES=16
```

## Switching Between Environments

You can easily switch between self-hosted Redis and a cloud provider by changing just the REDIS_URL:

```env
# For local development (self-hosted)
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:${REDIS_PORT}/${REDIS_DB}

# For cloud Redis (e.g., Upstash, Redis Labs)
REDIS_URL=redis://username:password@cloud-provider-host:port/db_number
```

## Port Configuration

Rather than hardcoding port numbers, all services now use the dynamically configured port variables:

```env
# Port Configuration
REDIS_PORT=6379          # Redis server port
GRAFANA_PORT=3000        # Grafana UI port 
PROMETHEUS_PORT=9090     # Prometheus metrics port
DJANGO_PORT=8000         # Django application port
```

## Redis Server Configuration

The Redis server is now fully configurable through environment variables:

```
redis-server --appendonly yes \
  --requirepass ${REDIS_PASSWORD} \
  --maxmemory 256mb \
  --maxmemory-policy allkeys-lru \
  --port ${REDIS_PORT} \
  --databases ${REDIS_DATABASES}
```

This makes it easy to:

1. Change the Redis listening port
2. Configure the total number of available databases
3. Adjust password, persistence, and memory settings

The Redis healthcheck command is also configured to use the same port:

```
redis-cli -a ${REDIS_PASSWORD} -p ${REDIS_PORT} ping
```

All services are configured to use these variables, making it easy to switch environments without changing Docker configurations.
