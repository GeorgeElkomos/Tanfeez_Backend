"""
Django settings for budget_transfer project.
"""

from pathlib import Path
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-budget-transfer-secret-key-change-this-in-production"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

##ALLOWED_HOSTS = ['127.0.0.1', 'localhost','185.197.251.203','budget-transfer-backend-production.up.railway.app']
ALLOWED_HOSTS = [
    "lightidea.org",
    "localhost",
    "127.0.0.1",
    "185.197.251.203",
    "www.lightidea.org",
]

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.admindocs",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "channels",
    "corsheaders",
    "user_management",
    "budget_management.apps.BudgetManagementConfig",
    "transaction",  # Add the new app
    "account_and_entitys",
    "Admin_Panel",
    "django_extensions",
    "approvals",
    "Chatting",
    "Invoice",
    "AI"
]

AUTH_USER_MODEL = "user_management.xx_User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,  # default page size
}


CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}


FIELD_ENCRYPTION_KEY = "G2g9Xb8qH-SZs-So5QEK1EXmf_lUqHuvdgFnitEtRB0="


MIDDLEWARE = [
    # 'budget_transfer.middleware.Encryption.EncryptionMiddleware',
    "budget_transfer.middleware.Sqlinjection.SQLInjectionProtectionMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "user_management.middleware.UserMiddleware",  # Updated middleware reference
]

ROOT_URLCONF = "budget_transfer.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # 'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = "budget_transfer.wsgi.application"


# Database
DATABASES = {
    "default":
    # {
    #     'ENGINE': 'django.db.backends.oracle',
    #     'NAME': 'PROD',  # Oracle SID or service name
    #     'USER': 'BUDGET_TRANSFER',  # Replace with your Oracle username
    #     'PASSWORD': 'KgJyrx3$1',  # Replace with your Oracle password
    #     'HOST': '185.197.251.203',  # Replace with your Oracle host
    #     'PORT': '1521',  # Default Oracle port
    # }
    {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # file-based SQLite DB
    }
}

CELERY_BEAT_SCHEDULE = {
    "check-sla-breaches": {
        "task": "approval.tasks.check_sla_breaches",
        "schedule": 300.0,  # every 5 min
    },
    "cleanup-delegations": {
        "task": "approval.tasks.cleanup_delegations",
        "schedule": 600.0,  # every 10 min
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


# Static files
STATIC_URL = "static/"
# STATICFILES_DIRS = [
#     BASE_DIR / 'static',
# ]


# Media files
MEDIA_URL = "/uploads/"
MEDIA_ROOT = BASE_DIR / "uploads"


# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# JWT settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}
# forward to https
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CORS settings
CORS_ALLOW_ALL_ORIGINS = True  # Only for development
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    "https://lightidea.org",
    "https://www.lightidea.org",
    "https://lightidea.org:9000",
    "https://budgettransfer.lightidea.org",
]

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
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
        "security_file": {
            "level": "WARNING",
            "class": "logging.FileHandler",
            "filename": "logs/security.log",
            "formatter": "verbose",
        },
        "budget_signals_file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "logs/budget_signals.log",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
    },
    "loggers": {
        "budget_transfer.middleware.Sqlinjection": {
            "handlers": ["console", "security_file"],
            "level": "WARNING",
            "propagate": False,
        },
        "budget_transfer_signals": {
            "handlers": ["console", "budget_signals_file"],
            "level": "INFO",
            "propagate": False,
        },
        "transaction_transfer_signals": {
            "handlers": ["console", "budget_signals_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
