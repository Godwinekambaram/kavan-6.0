"""
KAVAN v6.0 — Base Settings
============================================================
This module defines all shared configuration. Development
and Production settings import from here and override only
what is environment-specific.

All values are loaded from environment variables via
python-decouple to keep secrets out of source control.
"""

import os
from pathlib import Path

from decouple import Csv, config

# ============================================================
# PATHS
# ============================================================

# Build paths inside the project: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ============================================================
# APPLICATION IDENTITY
# ============================================================

APP_NAME = config("APP_NAME", default="KAVAN")
APP_VERSION = config("APP_VERSION", default="6.0.0")
APP_ENV = config("APP_ENV", default="development")
COMPANY_NAME = config("COMPANY_NAME", default="KAVAN Technologies")

# ============================================================
# SECURITY
# ============================================================

SECRET_KEY = config("SECRET_KEY", default="change-me-in-production")

DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1",
    cast=Csv(),
)

# ============================================================
# INSTALLED APPLICATIONS
# ============================================================

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
    "django_celery_beat",
    "django_celery_results",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.core.apps.CoreConfig",
    "apps.health.apps.HealthConfig",
    # ---- Layer 2: Identity & Access Management ----
    "apps.authentication.apps.AuthenticationConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.profiles.apps.ProfilesConfig",
    "apps.sessions.apps.SessionsConfig",
    "apps.devices.apps.DevicesConfig",
    "apps.mfa.apps.MFAConfig",
    "apps.audit.apps.AuditConfig",
    # ---- Layer 3: Tenant Lifecycle & Isolation ----
    "backend.apps.tenants.apps.TenantsConfig",
    # ---- Layer 4: Role-Based Access Control ----
    "backend.apps.rbac.apps.RbacConfig",
    # ---- Layer 5: Marketplace & Product Management ----
    "backend.apps.marketplace.apps.MarketplaceConfig",
    # ---- Layer 6: Deployment & Provisioning Engine ----
    "backend.apps.deployments.apps.DeploymentsConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ============================================================
# MIDDLEWARE
# ============================================================
# Order matters. See docs/ARCHITECTURE.md for flow diagram.

MIDDLEWARE = [
    # Security first
    "django.middleware.security.SecurityMiddleware",
    # Static files (must be before other middleware)
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # CORS (must be before CommonMiddleware)
    "corsheaders.middleware.CorsMiddleware",
    # Custom middleware
    "config.middleware.request_id.RequestIDMiddleware",
    "config.middleware.correlation.CorrelationIDMiddleware",
    "config.middleware.correlation.RequestContextMiddleware",
    "config.middleware.security.SecurityHeadersMiddleware",
    "config.middleware.security_hardening.SecurityHardeningMiddleware",
    "config.middleware.logging.RequestLoggingMiddleware",
    "config.middleware.exception_handler.ExceptionHandlerMiddleware",
    # Django built-ins
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "backend.apps.tenants.middleware.tenant_middleware.TenantMiddleware",
    "backend.apps.rbac.middleware.RBACMiddleware",
]

# ============================================================
# URL CONFIGURATION
# ============================================================

ROOT_URLCONF = "config.urls"

# ============================================================
# TEMPLATES
# ============================================================

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

# ============================================================
# WSGI / ASGI
# ============================================================

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ============================================================
# DATABASE
# ============================================================

DATABASES = {
    "default": {
        "ENGINE": config("DB_ENGINE", default="django.db.backends.postgresql"),
        "NAME": config("DB_NAME", default="kavan_db"),
        "USER": config("DB_USER", default="kavan_user"),
        "PASSWORD": config("DB_PASSWORD", default="kavan_secure_password"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
        "OPTIONS": {
            "connect_timeout": 10,
        },
        "CONN_MAX_AGE": 60,  # Persistent connections (seconds)
        "ATOMIC_REQUESTS": True,  # Wrap each request in a transaction
    }
}

# Default primary key type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom user model (Layer 2)
AUTH_USER_MODEL = "authentication.User"

# ============================================================
# CACHE (Redis)
# ============================================================

REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "CONNECTION_POOL_KWARGS": {"max_connections": 50},
        },
        "KEY_PREFIX": "kavan",
        "TIMEOUT": 300,  # 5 minutes default
    }
}

# ============================================================
# CELERY
# ============================================================

CELERY_BROKER_URL = config(
    "CELERY_BROKER_URL", default="redis://localhost:6379/0"
)
CELERY_RESULT_BACKEND = config(
    "CELERY_RESULT_BACKEND", default="redis://localhost:6379/1"
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes soft limit
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_RESULT_EXTENDED = True

# ============================================================
# PASSWORD HASHERS (Layer 2 — Argon2 primary)
# ============================================================
# Argon2 is OWASP's recommended memory-hard algorithm.
# Legacy PBKDF2 hashes remain readable during migration.

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",  # Primary
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",  # Fallback (legacy)
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

# ============================================================
# PASSWORD VALIDATION
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# ============================================================
# DJANGO REST FRAMEWORK
# ============================================================

REST_FRAMEWORK = {
    # Authentication (Layer 2 will add JWT)
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Permissions (Layer 4 will add RBAC)
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",  # Open for Layer 1
    ],
    # Pagination
    "DEFAULT_PAGINATION_CLASS": "common.pagination.custom_pagination.KavanPageNumberPagination",
    "PAGE_SIZE": config("API_PAGINATION_PAGE_SIZE", default=20, cast=int),
    # Renderers
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    # Parsers
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    # Exception handler
    "EXCEPTION_HANDLER": "common.utils.exception_handler.kavan_exception_handler",
    # Versioning
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1"],
    "VERSION_PARAM": "version",
    # OpenAPI Schema Class
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Throttling
    "DEFAULT_THROTTLE_CLASSES": [
        "config.throttling.KavanBurstThrottle",
        "config.throttling.KavanAnonRateThrottle",
        "config.throttling.KavanUserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": config("THROTTLE_RATE_ANON", default="100/day"),
        "user": config("THROTTLE_RATE_USER", default="1000/day"),
        "burst": config("THROTTLE_RATE_BURST", default="60/minute"),
    },
}

# ============================================================
# CORS
# ============================================================

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
    cast=Csv(),
)
CORS_ALLOW_ALL_ORIGINS = config("CORS_ALLOW_ALL_ORIGINS", default=False, cast=bool)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-request-id",
    "x-tenant-id",   # For Layer 3
]

# ============================================================
# INTERNATIONALIZATION
# ============================================================

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ============================================================
# STATIC FILES
# ============================================================

STATIC_URL = config("STATIC_URL", default="/static/")
STATIC_ROOT = BASE_DIR / config("STATIC_ROOT", default="staticfiles")
STATICFILES_DIRS = [
    BASE_DIR / "static",
] if (BASE_DIR / "static").exists() else []

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ============================================================
# MEDIA FILES
# ============================================================

MEDIA_URL = config("MEDIA_URL", default="/media/")
MEDIA_ROOT = BASE_DIR / config("MEDIA_ROOT", default="media")

# ============================================================
# EMAIL
# ============================================================

EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@kavan.com")

# ============================================================
# LOGGING (Base — overridden per environment)
# ============================================================

LOG_LEVEL = config("LOG_LEVEL", default="INFO")
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "common.logging.formatters.KavanJSONFormatter",
        },
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "json_file": {
            "level": LOG_LEVEL,
            "class": "common.logging.handlers.RotatingJSONFileHandler",
            "filename": LOG_DIR / "app.log",
            "maxBytes": 50 * 1024 * 1024,  # 50 MB
            "backupCount": 10,
            "formatter": "json",
        },
        "security_file": {
            "level": "WARNING",
            "class": "common.logging.handlers.RotatingJSONFileHandler",
            "filename": LOG_DIR / "security.log",
            "maxBytes": 50 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "json",
        },
        "error_file": {
            "level": "ERROR",
            "class": "common.logging.handlers.RotatingJSONFileHandler",
            "filename": LOG_DIR / "error.log",
            "maxBytes": 50 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "json",
        },
        "audit_file": {
            "level": "INFO",
            "class": "common.logging.handlers.RotatingJSONFileHandler",
            "filename": LOG_DIR / "audit.log",
            "maxBytes": 50 * 1024 * 1024,
            "backupCount": 30,
            "formatter": "json",
        },
        "celery_file": {
            "level": "WARNING",
            "class": "common.logging.handlers.RotatingJSONFileHandler",
            "filename": LOG_DIR / "celery.log",
            "maxBytes": 50 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "json",
        },
        "request_file": {
            "level": "INFO",
            "class": "common.logging.handlers.RotatingJSONFileHandler",
            "filename": LOG_DIR / "request.log",
            "maxBytes": 50 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "json",
        },
    },
    "loggers": {
        # Root logger
        "": {
            "handlers": ["console", "json_file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        # KAVAN application loggers
        "kavan": {
            "handlers": ["console", "json_file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "kavan.security": {
            "handlers": ["console", "security_file"],
            "level": "WARNING",
            "propagate": False,
        },
        "kavan.audit": {
            "handlers": ["audit_file"],
            "level": "INFO",
            "propagate": False,
        },
        "kavan.error": {
            "handlers": ["console", "error_file"],
            "level": "ERROR",
            "propagate": False,
        },
        # Django loggers
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "request_file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console", "security_file"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        # Third-party
        "celery": {
            "handlers": ["console", "celery_file"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# ============================================================
# API SETTINGS
# ============================================================

API_VERSION = config("API_VERSION", default="v1")
API_PAGINATION_PAGE_SIZE = config("API_PAGINATION_PAGE_SIZE", default=20, cast=int)
API_MAX_PAGE_SIZE = config("API_MAX_PAGE_SIZE", default=100, cast=int)

# ============================================================
# SESSION
# ============================================================

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# ============================================================
# SPECTACULAR SETTINGS
# ============================================================

from config.spectacular import SPECTACULAR_SETTINGS

