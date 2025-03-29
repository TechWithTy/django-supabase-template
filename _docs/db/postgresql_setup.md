# PostgreSQL Setup and Usage Guide

## Overview

This document provides comprehensive instructions for setting up, configuring, and working with PostgreSQL in the Django-Supabase template. PostgreSQL is a powerful, open-source object-relational database system with over 30 years of active development that has earned it a strong reputation for reliability, feature robustness, and performance.

## Local Development Setup

### Prerequisites

- PostgreSQL 12+ installed locally or running in Docker
- Python 3.8+ with Django 4.2+
- psycopg2-binary package (included in requirements.txt)

### Configuration

#### Environment Variables

The database connection is configured through environment variables in the `.env` file:

```
POSTGRES_DB=django_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=test123
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

#### Django Settings

The PostgreSQL connection is configured in `backend/core/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'django_db'),
        'USER': os.getenv('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'postgres'),
        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}
```

### Setup with Docker

The easiest way to set up PostgreSQL for development is using Docker Compose. The configuration is defined in `docker-compose.yml`:

```yaml
# PostgreSQL database service
postgres:
  image: postgres:14-alpine
  volumes:
    - postgres-data:/var/lib/postgresql/data
  environment:
    - POSTGRES_USER=postgres
    - POSTGRES_PASSWORD=postgres
    - POSTGRES_DB=django_db
  ports:
    - "5432:5432"
  networks:
    - app-network
```

To start PostgreSQL with Docker:

```bash
docker-compose up postgres
```

### Manual Setup (without Docker)

1. Install PostgreSQL on your system:

   - **Windows**: Download and install from [PostgreSQL website](https://www.postgresql.org/download/windows/)
   - **macOS**: Use Homebrew: `brew install postgresql`
   - **Linux**: Use package manager, e.g., `sudo apt install postgresql postgresql-contrib`

2. Create a database:
   ```bash
   sudo -u postgres psql
   CREATE DATABASE django_db;
   CREATE USER postgres WITH PASSWORD 'test123';
   ALTER ROLE postgres SET client_encoding TO 'utf8';
   ALTER ROLE postgres SET default_transaction_isolation TO 'read committed';
   ALTER ROLE postgres SET timezone TO 'UTC';
   GRANT ALL PRIVILEGES ON DATABASE django_db TO postgres;
   \q
   ```

## Database Migrations

### Creating Migrations

After defining or modifying Django models, create migrations:

```bash
python manage.py makemigrations
```

To create migrations for a specific app:

```bash
python manage.py makemigrations app_name
```

### Applying Migrations

To apply all pending migrations:

```bash
python manage.py migrate
```

To apply migrations for a specific app:

```bash
python manage.py migrate app_name
```

### Migration Order for Custom User Model

When using a custom user model (as in this template), the migration order is important:

1. First migrate the authentication app containing the custom user model:

   ```bash
   python manage.py makemigrations authentication
   python manage.py migrate authentication
   ```

2. Then migrate the remaining apps:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

## Testing Database Connection

### Using Django's dbshell

To test the database connection and interact with PostgreSQL through Django:

```bash
python manage.py dbshell
```

This opens a PostgreSQL interactive terminal where you can run SQL commands.

### Using Django's check command

To verify database connection configuration:

```bash
python manage.py check --database default
```

### Direct PostgreSQL Connection

To connect directly to PostgreSQL:

```bash
psql -U postgres -h localhost -p 5432 django_db
```

Or with Docker:

```bash
docker-compose exec postgres psql -U postgres -d django_db
```

## Common PostgreSQL Commands

Once connected to PostgreSQL with `psql`:

- List all databases: `\l`
- Connect to a database: `\c database_name`
- List all tables: `\dt`
- Describe a table: `\d table_name`
- Execute SQL query: `SELECT * FROM table_name LIMIT 5;`
- Exit psql: `\q`

## Database Optimization

### Indexing

Create indexes on fields that are frequently queried:

```python
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    supabase_uid = models.CharField(max_length=255, db_index=True)  # Add index
```

### Query Optimization

- Use `select_related()` and `prefetch_related()` to reduce database queries
- Use `values()` or `values_list()` when you only need specific fields
- Add appropriate indexes to fields used in filtering and ordering

### Connection Pooling

For production, consider using connection pooling with pgBouncer or Django's built-in connection pooling.

## Backup and Restore

### Creating Backups

```bash
pg_dump -U postgres -h localhost -p 5432 -F c -b -v -f backup.dump django_db
```

With Docker:

```bash
docker-compose exec postgres pg_dump -U postgres -F c -b -v -f /tmp/backup.dump django_db
docker cp $(docker-compose ps -q postgres):/tmp/backup.dump ./backup.dump
```

### Restoring Backups

```bash
pg_restore -U postgres -h localhost -p 5432 -d django_db -v backup.dump
```

With Docker:

```bash
docker cp ./backup.dump $(docker-compose ps -q postgres):/tmp/backup.dump
docker-compose exec postgres pg_restore -U postgres -d django_db -v /tmp/backup.dump
```

## Production Considerations

### Security

1. **Strong Passwords**: Use strong, unique passwords for database users
2. **Network Security**: Restrict database access to specific IP addresses
3. **SSL**: Enable SSL connections for encrypted data transmission
4. **Regular Updates**: Keep PostgreSQL updated with security patches

### Performance Tuning

Key PostgreSQL configuration parameters to consider adjusting in `postgresql.conf`:

- `shared_buffers`: 25% of system memory for dedicated servers
- `effective_cache_size`: 50-75% of system memory
- `work_mem`: 32-64MB (depends on concurrent connections)
- `maintenance_work_mem`: 256MB-1GB for maintenance operations
- `max_connections`: Adjust based on expected concurrent connections

## Troubleshooting

### Common Issues

1. **Connection Refused**:

   - Verify PostgreSQL is running
   - Check host, port, username, and password
   - Ensure PostgreSQL is configured to accept connections

2. **Authentication Failed**:

   - Verify username and password
   - Check `pg_hba.conf` for authentication settings

3. **Relation Does Not Exist**:

   - Ensure migrations have been applied
   - Check table name and schema

4. **Permission Denied**:
   - Verify user has appropriate permissions
   - Grant necessary privileges to the user

## Additional Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Django Database API](https://docs.djangoproject.com/en/stable/topics/db/)
- [Django PostgreSQL-specific Features](https://docs.djangoproject.com/en/stable/ref/contrib/postgres/)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)
