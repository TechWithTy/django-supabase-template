# Django + Supabase Template

A robust Django template with Supabase authentication integration, designed for scalable API development.

## Features

- 🔐 **Secure Authentication** via Supabase JWT validation
- 🚦 **Rate Limiting & Credit Tracking** for API usage control
- 📊 **Logging & Error Monitoring** with Sentry integration
- 🐳 **Dockerized Deployment** for consistent environments
- 🗄️ **Flexible ORM Options** with Django ORM and optional Drizzle ORM support
- 🚀 **CI/CD Pipeline Integration** for automated deployments

## Project Structure

```
django-supabase-template/
├── backend/             # Django application code
├── config/              # Environment and configuration files
├── docker/              # Docker-related files
├── docs/                # API documentation
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

## API Rate Limiting & Credit System

The template includes:

- Per-user rate limiting via Django REST Framework throttling
- Credit-based usage tracking for premium features
- API endpoints to check remaining credits

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

3. **Admin Interface**:
   You can also manage credit usage rates through the Django admin interface by navigating to the `Credit Usage Rates` section.

## Integrating the Complete SaaS Backend into an Existing Python Project

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
   In your existing Django project's `settings.py`, add the necessary apps and configurations:

   ```python
   INSTALLED_APPS = [
       # Existing apps
       ...,
       # New apps
       'apps.credits',
       'apps.authentication',
       'apps.users',
       'django_prometheus',
   ]

   # Add Prometheus middleware
   MIDDLEWARE = [
       'django_prometheus.middleware.PrometheusBeforeMiddleware',
       # Your existing middleware
       ...,
       'django_prometheus.middleware.PrometheusAfterMiddleware',
   ]

   # Configure Celery
   CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
   CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
   ```

7. **Configure Authentication**:
   Set up Supabase authentication in your project:

   ```python
   # Add to settings.py
   REST_FRAMEWORK = {
       'DEFAULT_AUTHENTICATION_CLASSES': [
           'apps.authentication.authentication.SupabaseAuthentication',
           # Your existing authentication classes
       ],
   }

   # Supabase settings
   SUPABASE_URL = os.environ.get('SUPABASE_URL')
   SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
   ```

8. **Set Up Celery**:
   Create or modify your `celery.py` file to include task queues:

   ```python
   # celery.py
   from __future__ import absolute_import, unicode_literals
   import os
   from celery import Celery

   os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')

   app = Celery('your_project')
   app.config_from_object('django.conf:settings', namespace='CELERY')
   app.autodiscover_tasks()
   ```

9. **Run Migrations**:
   Apply the database migrations:

   ```bash
   python manage.py migrate
   ```

10. **Create Custom Endpoints**:
    Extend the existing views or create new ones for your specific business logic:

    ```python
    # your_app/views.py
    from apps.credits.throttling import CreditBasedThrottle
    from rest_framework.views import APIView
    from rest_framework.response import Response

    class YourCustomEndpoint(APIView):
        throttle_classes = [CreditBasedThrottle]

        def post(self, request):
            # Your custom logic here
            return Response({"result": "success"})
    ```

11. **Configure Credit Usage Rates**:
    Set up credit costs for your custom endpoints:

    ```bash
    python manage.py shell
    ```

    ```python
    from apps.credits.models import CreditUsageRate
    CreditUsageRate.objects.create(endpoint_path='/api/your-endpoint/', credits_per_request=5)
    ```

12. **Start the Full Stack**:
    Launch the entire application stack using Docker Compose:

    ```bash
    docker-compose up -d
    ```

13. **Access Services**:

    - Django API: http://localhost:8000/api/
    - Django Admin: http://localhost:8000/admin/
    - Prometheus: http://localhost:9090/

14. **Deploy Your SaaS API**:
    Use the included CI/CD workflows to deploy your application to your preferred hosting provider.

15. **Monitor and Scale**:
    Use Prometheus metrics to monitor usage and performance, and scale your services as needed.

## Monitoring & Error Tracking

- Prometheus metrics exposed at `/metrics`
- Sentry integration for error tracking and performance monitoring

## Deployment

The project is fully Dockerized and includes CI/CD pipeline configurations for:

- GitHub Actions
- GitLab CI

## License

MIT
