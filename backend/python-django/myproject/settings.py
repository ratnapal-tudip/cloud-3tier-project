"""
Django settings for myproject project.
Cloud 3-Tier Backend — raw MySQL queries only, no Django ORM auth system.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-%s2z!!3u%7s#(p@lrc^)yyokp1c!el)k+$(c)qqaek+2%u7m&a')

# JWT config (mirrors FastAPI)
JWT_SECRET_KEY = os.getenv('SECRET_KEY', 'super-secret-dev-key-change-in-production')
JWT_ALGORITHM  = 'HS256'
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

DEBUG = True
ALLOWED_HOSTS = ['*']

# ---------------------------------------------------------------------------
# Minimal apps — no Django contrib auth/admin/sessions/contenttypes
# We use raw MySQL queries with our own users table.
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'rest_framework',
    'corsheaders',
    'myproject.auth_app',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'myproject.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {'context_processors': []},
    },
]

WSGI_APPLICATION = 'myproject.wsgi.application'

# ---------------------------------------------------------------------------
# MySQL — same creds as FastAPI, our schema is in database/data.sql
# ---------------------------------------------------------------------------
MYSQL_HOST     = os.getenv('MYSQL_HOST')
MYSQL_PORT     = int(os.getenv('MYSQL_PORT'))
MYSQL_USER     = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')

# Django needs DATABASES set even if we use raw connections.
DATABASES = {
    'default': {
        'ENGINE': 'mysql.connector.django',
        'NAME': MYSQL_DATABASE,
        'USER': MYSQL_USER,
        'PASSWORD': MYSQL_PASSWORD,
        'HOST': MYSQL_HOST,
        'PORT': MYSQL_PORT,
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}

# ---------------------------------------------------------------------------
# CORS — allow all origins (same as FastAPI allow_origins=["*"])
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES':     [],
    'UNAUTHENTICATED_USER': None,
}

# ---------------------------------------------------------------------------
# Internationalisation / Static files
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'UTC'
USE_I18N      = True
USE_TZ        = True
STATIC_URL    = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
