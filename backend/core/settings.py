import os
import sys
from pathlib import Path
from urllib.parse import urlparse
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from utils.sensitive import load_environment_files

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Add the apps directory to the Python path
sys.path.insert(0, str(BASE_DIR / "apps"))

# Load environment variables from .env file
load_environment_files()

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-key-for-dev-only")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "django_prometheus",
    "django_filters",
    "csp",  # Added for Content Security Policy
    "django.middleware.gzip",  # Added for response compression
]

LOCAL_APPS = [
    # Add your local apps here
    "apps.users",
    "apps.authentication",
    "apps.credits",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",  # Prometheus first
    "django.middleware.gzip.GZipMiddleware",  # Response compression
    "csp.middleware.CSPMiddleware",  # Added for Content Security Policy
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # CORS before CommonMiddleware
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Whitenoise for static files
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.authentication.middleware.SupabaseJWTMiddleware",  # Custom JWT middleware
    "django_prometheus.middleware.PrometheusAfterMiddleware",  # Prometheus last
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"
# Local PostgreSQL Configuration Variables
LOCAL_DB_NAME = os.getenv("POSTGRES_DB", "django_db")
LOCAL_DB_USER = os.getenv("POSTGRES_USER", "postgres")
LOCAL_DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "test123")
LOCAL_DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
LOCAL_DB_PORT = os.getenv("POSTGRES_PORT", "5432")

# Print local database configuration for debugging
print("Local PostgreSQL DB Config:")
print(f"Name: {LOCAL_DB_NAME}")
print(f"User: {LOCAL_DB_USER}")
print(f"Host: {LOCAL_DB_HOST}")
print(f"Port: {LOCAL_DB_PORT}")
print(f"Password: {'*' * len(LOCAL_DB_PASSWORD)}")  # Mask password

# Supabase Connec

# Get connection URL from environment
connection_url = os.getenv(
    "SUPABASE_DB_CONNECTION_STRING",
    "postgresql://postgres.yourconnection:[YOUR-PASSWORD]@aws-0-us-west-1.pooler.supabase.com:6543/postgres",
)
connection_url = connection_url.replace("[", "").replace("]", "")
print("Connection String:", connection_url)
parsed_url = urlparse(connection_url)
# Extract parsed values to variables
SUPABASE_DB_NAME = parsed_url.path.lstrip("/")
SUPABASE_DB_USER = parsed_url.username
SUPABASE_DB_HOST = parsed_url.hostname
SUPABASE_DB_PORT = parsed_url.port or "5432"
SUPABASE_DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD", "prod123")
SUPABASE_DB_CONNECTION_STRING = os.getenv(
    "SUPABASE_DB_CONNECTION_STRING", "No Connection String"
)

# Supabase API Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://thzqgzpbfcjuemcrqosf.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

# Print parsed values for debugging
print("Supabase DB Config:")
print(f"Name: {SUPABASE_DB_NAME}")
print(f"User: {SUPABASE_DB_USER}")
print(f"Host: {SUPABASE_DB_HOST}")
print(f"Port: {SUPABASE_DB_PORT}")
print(f"Password: {'*' * len(SUPABASE_DB_PASSWORD)}")  # Mask password
print(f"Connection String: {SUPABASE_DB_CONNECTION_STRING}")  # Mask password
print("Supabase URL:", SUPABASE_URL)

# Database configurations
DATABASES = {
    "local": {
        "ENGINE": "dj_db_conn_pool.backends.postgresql",
        "NAME": LOCAL_DB_NAME,
        "USER": LOCAL_DB_USER,
        "PASSWORD": LOCAL_DB_PASSWORD,
        "HOST": LOCAL_DB_HOST,
        "PORT": LOCAL_DB_PORT,
        "POOL_OPTIONS": {
            "POOL_SIZE": 20,
            "MAX_OVERFLOW": 10,
            "RECYCLE": 300,  # Connection recycle time in seconds
        },
    },
    "supabase": {
        "ENGINE": "dj_db_conn_pool.backends.postgresql",
        "NAME": SUPABASE_DB_NAME,
        "USER": SUPABASE_DB_USER,
        "PASSWORD": SUPABASE_DB_PASSWORD,
        "HOST": SUPABASE_DB_HOST,
        "PORT": SUPABASE_DB_PORT,
        "OPTIONS": {
            "sslmode": "require",  # Supabase requires SSL
        },
        "POOL_OPTIONS": {
            "POOL_SIZE": 20,
            "MAX_OVERFLOW": 10,
            "RECYCLE": 300,  # Connection recycle time in seconds
        },
    },
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Media files
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom user model
AUTH_USER_MODEL = "authentication.CustomUser"

# REST Framework settings
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.authentication.authentication.SupabaseJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "apps.credits.throttling.CreditBasedThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("DEFAULT_THROTTLE_RATES_ANON", "100/day"),
        "user": os.getenv("DEFAULT_THROTTLE_RATES_USER", "1000/day"),
        "premium": os.getenv("DEFAULT_THROTTLE_RATES_PREMIUM", "5000/day"),
    },
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer"
        if DEBUG
        else "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

# CORS settings
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(
    ","
)
CORS_ALLOW_CREDENTIALS = True

# Supabase settings
SUPABASE_DB_CONNECTION_STRING = os.getenv("SUPABASE_DB_CONNECTION_STRING")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

# Celery settings
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Redis settings
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Redis Cache Configuration
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://redis:6379/1"),
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

# Cache time to live is 15 minutes
CACHE_TTL = 60 * 15

# Use Redis for session store
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Use Redis for rate limiting
RATELIMIT_USE_REDIS = True
RATELIMIT_REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/2")

# Sentry settings
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN and not DEBUG:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
        ],
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        traces_sample_rate=0.1,
        # Send performance metrics for all sampled transactions
        enable_tracing=True,
        # If you wish to associate users to errors
        send_default_pii=True,
        environment=os.getenv("ENVIRONMENT", "production"),
    )

# Security settings - enhanced for production
if not DEBUG:
    # HTTPS/SSL settings
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    # Session security settings
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True

    # Security headers
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = "DENY"  # Prevents clickjacking

    # Content Security Policy
    CSP_DEFAULT_SRC = ("'self'",)
    CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https://fonts.googleapis.com")
    CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "'unsafe-eval'")
    CSP_FONT_SRC = ("'self'", "https://fonts.gstatic.com")
    CSP_IMG_SRC = ("'self'", "data:", "https:")

    # Rate limiting - already configured in REST_FRAMEWORK

    # Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs" / "django.log",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True,
        },
        "apps": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

# Create logs directory if it doesn't exist
logs_dir = BASE_DIR / "logs"
logs_dir.mkdir(exist_ok=True)
