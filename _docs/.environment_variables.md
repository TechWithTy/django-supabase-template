# Environment Variables Reference

This document provides a comprehensive overview of all environment variables used in the Django-Supabase template project. Use this as a reference when configuring your development, staging, or production environments.

## Core Django Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DJANGO_SECRET_KEY` | Django's secret key for cryptographic signing | None | Yes |
| `DJANGO_DEBUG` | Debug mode flag ("True" or "False") | "False" | No |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated list of allowed hosts | "localhost,127.0.0.1" | No |
| `APP_VERSION` | Application version for health checks | "dev" | No |

## Supabase Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SUPABASE_URL` | URL of your Supabase project | None | Yes |
| `SUPABASE_ANON_KEY` | Anon/public key for Supabase client | None | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (admin access) | None | Yes |
| `SUPABASE_JWT_SECRET` | JWT secret for token validation | None | Yes |

## Database Configuration

Note: For development, SQLite is used by default. For production, Supabase PostgreSQL is used.

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | Database connection URL (if not using SQLite) | None | No |

## Redis and Caching

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `REDIS_URL` | Redis connection URL | "redis://redis:6379/0" | No |
| `CACHE_TTL` | Cache time-to-live in seconds | 900 (15 minutes) | No |

## Celery Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `CELERY_BROKER_URL` | Celery broker URL (usually Redis) | "redis://redis:6379/0" | No |
| `CELERY_RESULT_BACKEND` | Celery result backend URL | "redis://redis:6379/0" | No |

## Rate Limiting

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DEFAULT_THROTTLE_RATES_ANON` | Rate limit for anonymous users | "100/day" | No |
| `DEFAULT_THROTTLE_RATES_USER` | Rate limit for authenticated users | "1000/day" | No |
| `DEFAULT_THROTTLE_RATES_PREMIUM` | Rate limit for premium users | "5000/day" | No |
| `RATELIMIT_USE_REDIS` | Whether to use Redis for rate limiting | True | No |
| `RATELIMIT_REDIS_URL` | Redis URL for rate limiting | "redis://redis:6379/2" | No |

## Credit System

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DEFAULT_CREDIT_COST` | Default credit cost for operations | 1 | No |
| `SCRIPT_EXECUTION_CREDIT_COST` | Credit cost for script execution | 5 | No |
| `CREDIT_OVERRIDE_ENABLED` | Allow admin override of credit costs | True | No |

## Monitoring and Error Tracking

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SENTRY_DSN` | Sentry DSN for error tracking | None | No |
| `SENTRY_TRACES_SAMPLE_RATE` | Sentry performance tracking sample rate | 0.1 | No |

## CORS and Security

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `CORS_ALLOWED_ORIGINS` | Comma-separated list of allowed origins | "http://localhost:3000" | No |
| `CORS_ALLOW_CREDENTIALS` | Allow credentials in CORS requests | True | No |

## Deployment

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DOMAIN` | Primary domain name | None | Yes (prod) |
| `GITHUB_REPOSITORY` | GitHub repository name for Docker images | None | Yes (CI/CD) |

## Example Configuration

### Development Environment (.env)

```env
DJANGO_SECRET_KEY=dev-secret-key-change-me-in-production
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret

REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Production Environment (.env.production)

```env
DJANGO_SECRET_KEY=your-secure-production-secret-key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret

REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

DOMAIN=yourdomain.com

SENTRY_DSN=your-sentry-dsn
```
