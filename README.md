# Django + Supabase Template

A robust Django template with Supabase authentication integration, designed for scalable API development with built-in credit system, monitoring, and deployment solutions.

## Supabase Integration

This template leverages Supabase as a powerful backend service that provides authentication, database, and storage capabilities with minimal configuration.

### Core Supabase Features

- 🔑 **JWT Authentication**: Secure token-based authentication with Supabase Auth
- 🛡️ **Row Level Security (RLS)**: Database-level multi-tenant data isolation
- 🪣 **Storage Buckets**: Managed file storage with security policies
- 🔄 **Real-time Subscriptions**: Live data updates for web and mobile clients
- 🧩 **Serverless Edge Functions**: Deploy custom logic to the edge

### Authentication Flow

1. Users authenticate through Supabase (OAuth, email/password, phone, magic link)
2. Supabase issues a JWT token with custom claims
3. Django middleware validates the JWT token for protected routes
4. Claims from the JWT token define user permissions and tenant access

### Multi-Tenancy Implementation

The template includes a comprehensive multi-tenancy solution using Supabase's Row Level Security:

```sql
-- Enable RLS on tables
ALTER TABLE your_table ENABLE ROW LEVEL SECURITY;

-- Create tenant isolation policy
CREATE POLICY tenant_isolation ON your_table 
  FOR ALL USING (tenant_id = auth.jwt() -> 'app_metadata' ->> 'tenant_id');
```

#### Key Multi-Tenancy Features:

- Database-level data isolation between tenants
- Automatic tenant context from JWT claims
- Middleware for maintaining tenant context in Django
- Built-in tenant management through Django admin

### Credit System Integration

The template's credit system works seamlessly with Supabase through:

1. **Credit Decorator**: Apply `@with_credits(credit_amount=5)` to any view
2. **Credit Utility Function**: Wrap any function with credit-based access control
3. **Database Integration**: Track credit transactions with Supabase RLS policies

### Supabase Setup

1. **Create a Supabase Project**:
   - Sign up at [supabase.com](https://supabase.com)
   - Create a new project and note your project URL and API keys

2. **Configure Environment Variables**:

```bash
# .env file
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_PUBLIC_KEY=your-public-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret
```

3. **Enable Required Features**:
   - Configure authentication providers in the Supabase dashboard
   - Enable Row Level Security for database tables
   - Create storage buckets with appropriate policies

4. **Deploy Edge Functions** (optional):
   - Use the Supabase CLI to deploy serverless functions
   - Connect edge functions to your Django API endpoints

### Advanced SQL Functions

The template includes utility SQL functions for advanced use cases:

```sql
-- Create a function to execute arbitrary SQL (admin only)
CREATE OR REPLACE FUNCTION exec_sql(query text)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  EXECUTE query;
END;
$$;

-- Grant access to authenticated users (or restrict to service_role if preferred)
GRANT EXECUTE ON FUNCTION exec_sql(text) TO authenticated;
```

## Features

- 🔐 **Secure Authentication** via Supabase JWT validation
- 🚦 **Rate Limiting & Credit System** with concurrency-safe credit tracking for API usage
- 📊 **Monitoring & Observability** with Prometheus metrics and structured logging
- 🐳 **Production-Ready Deployment** with Docker, Hetzner Cloud, and Coolify support
- 🔄 **Async Task Processing** with Redis and Celery integration
- 🗄️ **Flexible ORM Options** with Django ORM and optional Drizzle ORM support
- 🚀 **CI/CD Pipeline Integration** for automated deployments
- 💳 **Subscription Management**: Create and manage subscription plans
- 💳 **Stripe Integration**: Manage subscriptions, webhooks, and credit allocation
- 💳 **Credit System**: Manage credits for API usage
- 💳 **Testing**: Comprehensive test cases for Each app and view

## Project Structure

```
django-supabase-template/
├── backend/             # Django application code
├── config/              # Environment and configuration files
├── docker/              # Docker-related files
├── _docs/               # Project documentation
├── .env.example         # Example environment variables
├── docker-compose.yml   # Docker Compose configuration
├── requirements.txt     # Python dependencies
└── README.md            # Project documentation
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git
- Supabase account and project
- Stripe account and API keys
- Hetzner Cloud account and API keys
- Coolify account and API keys
- Supabase Api Keys Or Self Hosted
- Optional Drizzle ORM
- Optional PostgreSQL Database

### Setup Steps

1. **Clone the repository**

```bash
git clone https://github.com/your-org/django-supabase-template.git
cd django-supabase-template
```

2. **Configure environment variables**

```bash
cp .env.example .env
# Edit .env with your Supabase credentials and other settings
```

3. **Start the services**

```bash
docker-compose up --build
```

4. **Apply database migrations**

```bash
docker exec -it backend python manage.py migrate
```

5. **Access the API**

The API will be available at http://localhost:8000/api/

## Setup Integration Script

To simplify the integration of the Supabase template into your existing Python project, you can use the provided setup script. This script will copy all necessary files and configurations from the template into your project.

### Features

- **Copies all necessary files and folders** from the template to your project
- **Merges requirements.txt** if both your project and the template have them
- **Preserves existing files** in your project while adding new ones
- **Handles configuration files** like `.env`, `docker-compose.yml`, etc.

### Usage

1. **Run the Setup Script**:
   After cloning the repository, navigate to the project directory and run the script:

   ```bash
   python _setup_integration.py /path/to/your/existing/project
   ```

   This will copy all files and directories (except the script itself) to your project, including:

   - `.env.example` as `.env`
   - `docker-compose.yml`
   - `config` folder (for Prometheus)
   - `database` folder
   - `docker` folder (containing Dockerfile)
   - All other necessary files

2. **requirements.txt Merging**:
   The project uses requirements.txt to manage dependencies. If your existing project has a `requirements.txt` and the template also has one, the script will intelligently merge them, preserving your existing dependencies while adding the ones required by the template.

3. **Follow the Remaining Setup Steps**:
   After running the script, follow the remaining setup steps in the README to configure your project.


## Authentication Flow

1. Users authenticate through Supabase (OAuth, email/password, OTP)
2. Supabase issues a JWT token
3. Django validates the JWT token using middleware
4. Role-based access control is enforced based on Supabase claims

## Enhanced Credit System

The template includes a robust credit system with advanced features:

### Core Features

- Per-user rate limiting via Django REST Framework throttling
- Credit-based usage tracking for premium features
- API endpoints to check remaining credits
- Concurrency-safe credit operations with row-level locking
- Credit hold mechanism for long-running operations
- UUID primary keys for distributed environments
- Structured logging for comprehensive auditing

### Monitoring and Observability

- Prometheus metrics for tracking credit transactions and balances
- Performance measurement with duration metrics and failure tracking
- Integration with monitoring dashboards

## Managing Credits for API Endpoints

### Using CreditUsageRate

The `CreditUsageRate` model allows administrators to define credit costs for different API endpoints. Here's how to use it:

1. **Create a New Credit Usage Rate**:
   You can create a new credit usage rate for an endpoint in the Django shell or through the admin interface:

   ```python
   from apps.credits.models import CreditUsageRate

   new_rate = CreditUsageRate.objects.create(
       endpoint_path='/api/resource/',  # The API endpoint
       credits_per_request=5,            # Set the number of credits for this endpoint
       description='Cost for accessing the resource endpoint',
       is_active=True                     # Set to True to make it active
   )
   ```

2. **Update Existing Credit Usage Rates**:
   If you need to change the credit cost for an existing endpoint, fetch the instance and update it:

   ```python
   existing_rate = CreditUsageRate.objects.get(endpoint_path='/api/resource/')
   existing_rate.credits_per_request = 3  # Set new credit cost
   existing_rate.save()                    # Save changes
   ```

3. **Managing Credit Holds**:
   For long-running operations, you can place a hold on credits:

   ```python
   from apps.credits.models import CreditHold

   # Place a hold on 10 credits
   hold = CreditHold.place_hold(
       user=request.user,
       amount=10,
       description="Long-running task",
       endpoint="/api/long-task/"
   )

   # Later, release or consume the hold
   if task_successful:
       hold.consume()  # Convert hold to an actual deduction
   else:
       hold.release()  # Release the hold without charging credits
   ```

## Redis Caching Implementation

The template includes a powerful Redis caching system to improve application performance, reduce database load, and enhance scalability.

### Features

- 🚀 **High-Performance Caching**: In-memory storage for frequently accessed data
- 🔄 **Smart Invalidation**: Maintains data consistency across operations
- 🔑 **Structured Cache Keys**: Organized cache key patterns for different data types
- 🧩 **Multiple Caching Patterns**: Function results, API responses, database queries, and more
- 🔍 **Monitoring**: Cache hit/miss metrics for performance analysis
- 🧪 **Testable Design**: Comprehensive testing utilities and patterns

### Architecture

The Redis caching implementation serves multiple purposes:

1. **Django Cache Backend**: Primary cache backend for Django
2. **Session Storage**: Fast, in-memory session storage
3. **Celery Message Broker**: Backend for asynchronous task processing
4. **Rate Limiting**: Efficient implementation of API rate limiting
5. **Pub/Sub Messaging**: For real-time features

### Configuration

Redis is pre-configured in the template with production-ready settings:

```python
# Redis Configuration in settings.py
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Cache Configuration
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PARSER_CLASS": "redis.connection.HiredisParser",
            "CONNECTION_POOL_CLASS": "redis.BlockingConnectionPool",
            "CONNECTION_POOL_CLASS_KWARGS": {
                "max_connections": 50,
                "timeout": 20,
            },
            "MAX_CONNECTIONS": 1000,
            "IGNORE_EXCEPTIONS": True,
        },
    }
}
```

### Caching Strategies

The template implements several caching strategies:

#### 1. Function Result Caching

```python
from apps.caching.utils.redis_cache import cache_result

@cache_result(timeout=60 * 15)  # Cache for 15 minutes
def expensive_calculation(param1, param2):
    # Complex operation here
    return result
```

#### 2. API Response Caching

```python
from rest_framework.decorators import api_view
from apps.caching.utils.redis_cache import cache_result

@api_view(['GET'])
@cache_result(timeout=300)  # Cache for 5 minutes
def get_data(request):
    # Expensive database queries or API calls
    return Response(data)
```

#### 3. Database Query Caching

```python
from django.core.cache import cache
import hashlib

def get_user_stats(user_id):
    # Generate cache key
    cache_key = f"user_stats:{user_id}"
    
    # Try to get from cache
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data
        
    # If not in cache, fetch and store
    stats = UserStats.objects.filter(user_id=user_id).annotate(
        # Complex aggregations here
    ).values('counts', 'averages')
    
    # Cache for 1 hour
    cache.set(cache_key, stats, 3600)
    return stats
```

#### 4. Invalidation Patterns

```python
from django.core.cache import cache

def update_user(user_id, data):
    # Update the user
    user = User.objects.get(id=user_id)
    user.update(**data)
    
    # Invalidate all related cache keys
    cache_keys = [
        f"user:{user_id}",
        f"user_stats:{user_id}",
        "all_users"
    ]
    cache.delete_many(cache_keys)
    
    return user
```

### Cache Key Design

The template follows these patterns for cache key generation:

- **User Authentication**: `auth:user:{hashed_token}`
- **Database Queries**: `db_query:{table}:{hashed_query_params}`
- **Storage Operations**: `storage:list:{bucket_name}:{hashed_path}`

### Performance Considerations

- **Timeout Selection**: Cache timeouts are configured based on data volatility
- **Memory Management**: Selective caching to optimize memory usage
- **Connection Pooling**: Configured with optimal connection limits

### Testing Redis Caching

The template includes comprehensive testing utilities:

```python
# In your test file
from django.core.cache import cache
from django.test import TestCase, override_settings

@override_settings(CACHES={
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
})
class CacheTest(TestCase):
    def setUp(self):
        cache.clear()
    
    def tearDown(self):
        cache.clear()
    
    def test_cache_hit(self):
        # Test that caching works as expected
        cache.set('test_key', 'test_value', 10)
        self.assertEqual(cache.get('test_key'), 'test_value')
```

See the detailed documentation in `_docs/redis/` for more information on caching strategies, implementation patterns, and testing approaches.

## Grafana Monitoring

The template includes comprehensive monitoring with Grafana dashboards for visualizing application metrics and system performance.

### Features

- 📊 **Real-time Dashboards**: Pre-configured dashboards for API and system monitoring
- 🔍 **API Performance Metrics**: Request rates, latency, error rates, and anomaly detection
- 💻 **System Monitoring**: CPU, memory, disk, and network usage metrics
- 📱 **Container Insights**: Resource utilization for containerized services
- ⚠️ **Alerting Capabilities**: Set up notifications for critical conditions

### Architecture

The monitoring stack consists of:

- **Django Monitoring App**: Collects and exposes metrics from your application
- **Prometheus**: Scrapes and stores metrics from various sources
- **Grafana**: Visualizes metrics with interactive dashboards
- **Node Exporter**: Provides host system metrics (CPU, memory, disk)
- **cAdvisor**: Collects container-level metrics

### Quick Start

1. **Start the Monitoring Stack**

```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

2. **Access the Grafana Dashboard**

Open your browser and navigate to [http://localhost:3000](http://localhost:3000)

Default credentials:
- Username: `admin`
- Password: `admin`

3. **View the Pre-configured Dashboards**

Navigate to Dashboards > Browse > Django API Monitoring

### Available Dashboards

1. **Django API Monitoring Dashboard**
   - API Request Rate by endpoint
   - Response Time metrics (95th percentile)
   - Error Rate tracking
   - Credit Usage monitoring
   - Active User tracking

2. **System Overview Dashboard**
   - Host resource utilization
   - Container performance metrics
   - Network traffic analysis

See the detailed documentation in `_docs/grafana/` for more information on customizing dashboards, setting up alerts, and adding custom metrics.

## Production Deployment

For detailed deployment instructions, see the [deployment documentation](./_docs/deployment.md).

### Supported Deployment Platforms

- **Hetzner Cloud**: Complete instructions for setting up on Hetzner Cloud servers
- **Coolify**: Step-by-step guide for deploying with the Coolify platform

### Environment Variables

For a comprehensive list of environment variables and their descriptions, see the [environment variables reference](./_docs/environment_variables.md).

## Monitoring Setup

The template includes Prometheus integration for monitoring:

1. **Metrics Collection**:

   - API endpoint response times
   - Credit transactions and balances
   - Task queue performance

2. **Prometheus Configuration**:

   - Pre-configured prometheus.yml in the config directory
   - Django-prometheus integration for easy metrics exposure

3. **Dashboard Integration**:
   - Ready to integrate with Grafana for visualization

## Documentation

Comprehensive documentation is available in the `_docs/` directory

## License

MIT
