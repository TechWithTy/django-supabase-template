# Django + Supabase Template

A robust Django template with Supabase authentication integration, designed for scalable API development with built-in credit system, monitoring, and deployment solutions.

## Features

- 🔐 **Secure Authentication** via Supabase JWT validation
- 🚦 **Rate Limiting & Credit System** with concurrency-safe credit tracking for API usage
- 📊 **Monitoring & Observability** with Prometheus metrics and structured logging
- 🐳 **Production-Ready Deployment** with Docker, Hetzner Cloud, and Coolify support
- 🔄 **Async Task Processing** with Redis and Celery integration
- 🗄️ **Flexible ORM Options** with Django ORM and optional Drizzle ORM support
- 🚀 **CI/CD Pipeline Integration** for automated deployments

## Project Structure

```
django-supabase-template/
├── backend/             # Django application code
├── config/              # Environment and configuration files
├── docker/              # Docker-related files
├── _docs/               # Project documentation
├── .env.example         # Example environment variables
├── docker-compose.yml   # Docker Compose configuration
└── README.md            # Project documentation
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git
- Supabase account and project

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
- **Merges Pipfiles** if both your project and the template have them
- **Preserves existing files** in your project while adding new ones
- **Handles configuration files** like `.env`, `docker-compose.yml`, etc.

### Usage

1. **Run the Setup Script**:
   After cloning the repository, navigate to the project directory and run the script:

   ```bash
   python setup_integration.py /path/to/your/existing/project
   ```

   This will copy all files and directories (except the script itself) to your project, including:

   - `.env.example` as `.env`
   - `docker-compose.yml`
   - `config` folder (for Prometheus)
   - `database` folder
   - `docker` folder (containing Dockerfile)
   - All other necessary files

2. **Pipfile Merging**:
   We suggest using Pipfile to manage dependencies in your project. If your existing project has a `Pipfile` and the template also has one, the script will attempt to merge them, preserving your existing dependencies while adding the ones required by the template.

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

Comprehensive documentation is available in the `_docs/` directory:

- [Deployment Guide](./_docs/deployment.md)
- [Environment Variables](./_docs/environment_variables.md)
- [Credit System Documentation](./_docs/credit_based_views.md)
- [Project Roadmap](./_docs/_Roadmap.md)

## Integrating into an Existing Python Project

To transform your existing Python project into a SaaS-ready API with monitoring, task queues, and credit management, follow these comprehensive steps:

1. **Clone the Repository**:
   Clone the entire repository into a directory adjacent to your existing project:

   ```bash
   git clone https://github.com/your-org/django-supabase-template.git
   ```

2. **Merge Project Structure**:
   Instead of just copying the backend directory, you'll want to integrate the entire project structure:

   - Copy the `docker-compose.yml` file to your project root
   - Copy the `config/prometheus.yml` directory to your project root
   - Copy the `.github/workflows` directory for CI/CD pipelines
   - Copy the `backend` directory to your project

3. **Configure Docker Compose**:
   Modify the `docker-compose.yml` file to match your project's needs. The file includes services for:

   - Django backend
   - Redis for caching and Celery
   - Celery for background tasks
   - Prometheus for monitoring

   Ensure the volume mappings and service names align with your project structure.

4. **Install Dependencies**:
   Add the required dependencies to your project:

   ```bash
   pip install -r backend/requirements.txt
   ```

5. **Configure Environment Variables**:
   Create a `.env` file based on the `.env.example` provided and configure:

   - Supabase credentials
   - Redis connection details
   - Other service configurations

6. **Integrate Apps into Your Django Project**:
   In your existing Django project's `settings.py`, add the necessary apps and configurations.

## License

MIT
