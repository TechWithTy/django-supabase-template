# Deployment Guide

This document provides instructions for deploying the Django-Supabase application to production environments using Hetzner Cloud or Coolify.

## Prerequisites

- A Supabase account and project set up
- Docker and Docker Compose installed on your server
- Domain name configured with DNS records pointing to your server
- SSH access to your server

## Environment Variables

Create a `.env.production` file with the following variables:

```env
# Django settings
DJANGO_SECRET_KEY=your-secure-secret-key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Supabase settings
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret

# Redis and Celery settings
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Rate limiting
DEFAULT_THROTTLE_RATES_ANON=100/day
DEFAULT_THROTTLE_RATES_USER=1000/day
DEFAULT_THROTTLE_RATES_PREMIUM=5000/day

# Domain settings
DOMAIN=yourdomain.com

# Optional: Sentry for error tracking
SENTRY_DSN=your-sentry-dsn
```

## Deployment to Hetzner Cloud

### Server Setup

1. Create a Hetzner Cloud server (minimum recommendation: CPX21 with 4GB RAM)
2. Set up a non-root user with sudo privileges:

```bash
adduser appuser
usermod -aG sudo appuser
```

3. Install Docker and Docker Compose:

```bash
# Update system and install dependencies
apt update && apt upgrade -y
apt install -y apt-transport-https ca-certificates curl software-properties-common

# Add Docker GPG key and repository
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

# Install Docker and Docker Compose
apt update
apt install -y docker-ce docker-compose

# Add user to docker group
usermod -aG docker appuser
```

### Application Deployment

1. Clone the repository:

```bash
mkdir -p /opt/django-supabase
cd /opt/django-supabase
git clone https://github.com/yourusername/django-supabase-template .
```

2. Create the environment file:

```bash
cp .env.example .env.production
nano .env.production  # Edit with your production settings
```

3. Start the application:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

4. Set up SSL with Certbot:

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

## Deployment to Coolify

Coolify is a self-hostable Heroku/Netlify alternative that simplifies the deployment process.

### Setup

1. Install Coolify on your server following the [official documentation](https://coolify.io/docs/installation/requirements)
2. Connect your Git repository to Coolify
3. Configure the build settings:
   - Specify the Dockerfile.prod location
   - Set all environment variables from the list above
   - Configure the health check endpoint: `/api/health/`
   - Set container restart policy to "unless-stopped"

4. Deploy the application through the Coolify dashboard

## Database Backups

Set up automatic database backups:

```bash
# Create a backup directory
mkdir -p /var/backups/postgres
chmod 700 /var/backups/postgres

# Create a backup script
cat > /usr/local/bin/backup-postgres.sh << 'EOF'
#!/bin/bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/postgres"
SUPABASE_DB_CONNECTION="postgresql://postgres:password@localhost:5432/postgres"

# Create backup
pg_dump $SUPABASE_DB_CONNECTION -F c -b -v -f "$BACKUP_DIR/backup_$TIMESTAMP.backup"

# Remove backups older than 30 days
find $BACKUP_DIR -type f -name "*.backup" -mtime +30 -delete
EOF

chmod +x /usr/local/bin/backup-postgres.sh

# Set up a daily cron job
echo "0 2 * * * root /usr/local/bin/backup-postgres.sh > /var/log/postgres-backup.log 2>&1" > /etc/cron.d/postgres-backup
chmod 644 /etc/cron.d/postgres-backup
```

## Scaling Considerations

- **Horizontal Scaling**: Increase the number of backend containers behind a load balancer
- **Vertical Scaling**: Increase CPU and RAM resources for the containers
- **Database Scaling**: Consider moving to a managed PostgreSQL service for high traffic
- **Caching**: Utilize Redis caching for frequently accessed data
- **CDN**: Use a CDN for serving static and media files

## Monitoring

The application includes Prometheus metrics. Set up Grafana to visualize these metrics:

```bash
docker run -d -p 3000:3000 --name grafana --network app-network grafana/grafana-oss
```

Import dashboards for Django and Redis monitoring.

## Troubleshooting

### Common Issues

1. **Container fails to start**: Check logs with `docker-compose -f docker-compose.prod.yml logs backend`
2. **Database connection errors**: Verify Supabase credentials and network access
3. **Health check fails**: Ensure the `/api/health/` endpoint is accessible
4. **High memory usage**: Check for memory leaks and consider increasing container limits

### Useful Commands

```bash
# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Restart services
docker-compose -f docker-compose.prod.yml restart

# Run migrations
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Create superuser
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```
