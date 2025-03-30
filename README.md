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

## Credit-Based System

This template includes a comprehensive credit-based system for controlling access to API endpoints, allowing you to monetize your API or control resource usage.

### Features

- 💰 **Credit-Based Access Control**: Restrict API endpoints based on user credit balance
- 🔐 **Admin Overrides**: Allow administrators to override credit requirements
- 📊 **Transaction Tracking**: Record all credit transactions for auditing
- 🔄 **Flexible Implementation**: Multiple ways to implement credit requirements

### Implementation Options

1. **Credit Decorator**

   - Use the `@with_credits(credit_amount=5)` decorator on any API view
   - Automatically handles credit verification and deduction
   - Located in `backend/apps/users/views/creditable_views/credit_script_view.py`

   ```python
   @api_view(["POST"])
   @permission_classes([IsAuthenticated])
   @with_credits(credit_amount=10)
   def process_data(request):
       # Expensive data processing logic
       return Response({"status": "success"})
   ```

2. **Credit Utility Function**

   - Non-intrusive way to add credit requirements to existing views
   - Wrap any function with credit-based access control
   - Located in `backend/apps/users/views/creditable_views/utility_view.py`

   ```python
   def generate_report(request):
       def report_generator(req):
           # Report generation logic
           return Response({"report": "generated"})

       return call_function_with_credits(report_generator, request, credit_amount=20)
   ```

3. **Script Execution View**
   - Dedicated view for running scripts with credit requirements
   - Configurable credit cost and admin override
   - Located in `backend/apps/users/views/creditable_views/main_view.py`

See the detailed documentation in `_docs/supabase/supabase_views_credit_functions.md` for more information.

## Celery Implementation

The template includes a robust Celery setup for handling asynchronous and scheduled tasks.

### Features

- 📋 **Task Queuing**: Process background tasks asynchronously
- ⏱️ **Scheduled Tasks**: Run periodic tasks using Celery Beat
- 🔄 **Task Management**: Monitor and manage tasks using Flower
- 🗄️ **Result Storage**: Store and retrieve task results

### Architecture

- **Redis Broker**: Used for message queuing between Django and Celery workers
- **Celery Workers**: Process tasks from the queue
- **Celery Beat**: Schedule periodic tasks
- **Flower**: Web interface for monitoring Celery tasks

### Usage

1. **Define Tasks**

   ```python
   # In your_app/tasks.py
   from celery import shared_task

   @shared_task
   def process_data(data):
       # Process data asynchronously
       result = do_heavy_processing(data)
       return result
   ```

2. **Call Tasks**

   ```python
   # In your view
   from your_app.tasks import process_data

   def api_endpoint(request):
       data = request.data

       # Call the task asynchronously
       task = process_data.delay(data)

       return Response({"task_id": task.id})
   ```

3. **Schedule Tasks**

   ```python
   # In settings.py
   from celery.schedules import crontab

   CELERY_BEAT_SCHEDULE = {
       'cleanup-expired-credit-holds': {
           'task': 'apps.credits.tasks.cleanup_expired_credit_holds',
           'schedule': crontab(minute='0', hour='*/3'),  # Run every 3 hours
       },
   }
   ```

See the detailed documentation in `_docs/celery/celery_setup.md` for more information.

## Stripe Integration

This template includes a complete Stripe integration for managing subscriptions, processing payments, and handling webhooks.

### Features

- 💳 **Subscription Management**: Create and manage subscription plans
- 🔄 **Webhooks**: Process Stripe events for subscription lifecycle
- 🧾 **Customer Portal**: Allow users to manage their billing and subscriptions
- 💰 **Credit Allocation**: Automatically assign credits based on subscription tiers
- 🧪 **Test Mode Support**: Full test environment support for development

### Setup

1. **Configure Stripe Environment Variables**:

```
# Stripe API Keys - Production
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# Stripe API Keys - Test Mode
STRIPE_SECRET_KEY_TEST=sk_test_xxx
STRIPE_PUBLISHABLE_KEY_TEST=pk_test_xxx
STRIPE_WEBHOOK_SECRET_TEST=whsec_test_xxx

# URLs for Redirect
STRIPE_SUCCESS_URL=http://localhost:3000/success
STRIPE_CANCEL_URL=http://localhost:3000/cancel
STRIPE_PORTAL_RETURN_URL=http://localhost:3000/account
```

2. **Configure Customer Portal Settings**:

   - In your Stripe Dashboard, go to [Customer Portal Settings](https://dashboard.stripe.com/test/settings/billing/portal)
   - Configure the branding, features, and products available in the portal
   - Save the settings to enable portal creation

3. **Create Subscription Plans**:

```python
from apps.stripe_home.models import StripePlan

# Create a monthly subscription plan
StripePlan.objects.create(
    name="Basic Plan",
    description="Basic subscription with 100 monthly credits",
    amount=1000,  # $10.00
    currency="usd",
    interval="month",
    initial_credits=100,
    monthly_credits=50  # Credits provided each billing cycle
)
```

4. **Access the API Endpoints**:
   - `/api/stripe/checkout/` - Create checkout sessions
   - `/api/stripe/webhook/` - Receive webhook events
   - `/api/stripe/customer-portal/` - Create customer portal sessions
   - `/api/stripe/subscription/` - Retrieve user subscription details
   - `/api/stripe/credits/` - View current credit balance

### Optimal Customer Flow

1. **Checkout Process**:

   - Customer selects a subscription plan
   - Application calls the checkout endpoint with the plan ID
   - Customer is redirected to Stripe Checkout
   - After successful payment, customer returns to success URL
   - Webhook processes the subscription creation

2. **Subscription Management**:

   - Customer accesses their account dashboard
   - Application provides a "Manage Subscription" button
   - Button calls the customer portal endpoint
   - Customer is redirected to Stripe Customer Portal
   - Changes made in the portal trigger webhooks for updates
   - Customers can manage payment methods.

3. **Credits Management**:
   - Credits are allocated based on subscription tier
   - Initial credits are provided at signup
   - Monthly credits are added each billing cycle
   - Customers can view their credit balance and history

### Dynamic Product/Subscription Checkout

The `CheckoutSessionView` supports dynamic product and subscription creation:

```python
# Example frontend call
fetch('/api/stripe/checkout/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    plan_id: 'price_xxx',
    success_url: 'https://yourdomain.com/success?session_id={CHECKOUT_SESSION_ID}',
    cancel_url: 'https://yourdomain.com/cancel'
  })
})
.then(res => res.json())
.then(data => {
  // Redirect to checkout session URL
  window.location.href = data.checkout_url;
});
```

### Testing

The template includes comprehensive test cases for the Stripe integration:

```bash
# Run all Stripe tests
python manage.py test apps.stripe_home.tests

# Run specific integration tests
python -m pytest apps/stripe_home/tests/test_integration.py -v
```

Test mode is automatically enabled in the test environment by checking `settings.TESTING`. When this is `True`, the integration will use the test API keys.

### Webhooks

To test webhooks locally, you can use the Stripe CLI:

```bash
stripe listen --forward-to http://localhost:8000/api/stripe/webhook/
```

The webhook handler supports the following events:

- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.payment_succeeded`
- `checkout.session.completed`

### Metadata for Credits

Stripe products and plans can include metadata for credits allocation:

```python
# Adding metadata to a Stripe product
stripe.Product.create(
  name="Premium Plan",
  metadata={
    "initial_credits": "500",  # Credits allocated on signup
    "monthly_credits": "100"   # Credits allocated each billing cycle
  }
)
```

The webhook handler reads this metadata and allocates credits accordingly when processing subscription events.

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

Comprehensive documentation is available in the `_docs/` directory

## License

MIT
