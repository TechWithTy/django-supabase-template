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

## Monitoring & Error Tracking

- Prometheus metrics exposed at `/metrics`
- Sentry integration for error tracking and performance monitoring

## Deployment

The project is fully Dockerized and includes CI/CD pipeline configurations for:
- GitHub Actions
- GitLab CI

## License

MIT
