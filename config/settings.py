"""Django settings for the Maison backend.

Everything environment-specific is read from env vars with a local-dev default,
so the same file runs unchanged on a laptop and on Railway. The one rule worth
knowing: media storage switches to Cloudflare R2 as soon as the four R2_* vars
are present, and falls back to the local `media/` directory when they are not.
"""
import os
import sys
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


def env(name, default=''):
    return os.environ.get(name, default).strip()


def env_bool(name, default=False):
    return env(name, str(default)).lower() in {'1', 'true', 'yes', 'on'}


def env_list(name, default=''):
    return [item.strip() for item in env(name, default).split(',') if item.strip()]


# Core

SECRET_KEY = env(
    'SECRET_KEY',
    'django-insecure-)e3-nbjrfxm&fvy9*$6v$%o11$=56k++&dbhe%d+px7fr)q3zc',
)

DEBUG = env_bool('DEBUG', True)

# The manifest static storage below needs a collectstatic run behind it, which
# the test runner has no reason to do.
TESTING = 'test' in sys.argv

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', '127.0.0.1,localhost')

# Railway injects the service's public hostname at runtime.
RAILWAY_DOMAIN = env('RAILWAY_PUBLIC_DOMAIN')
if RAILWAY_DOMAIN:
    ALLOWED_HOSTS.append(RAILWAY_DOMAIN)

CSRF_TRUSTED_ORIGINS = [
    'https://{}'.format(host)
    for host in ALLOWED_HOSTS
    if host not in {'127.0.0.1', 'localhost'} and not host.startswith('*')
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'corsheaders',
    'rest_framework',
    'storages',

    'products',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database - DATABASE_URL on Railway, SQLite locally.

DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///{}'.format(BASE_DIR / 'db.sqlite3'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files - served by WhiteNoise, never by R2.

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'


# Media storage
#
# Product imagery goes to Cloudflare R2 when configured. R2 is S3-compatible,
# so django-storages' S3 backend drives it; the differences that matter are
# `region_name='auto'`, no ACLs (R2 rejects them) and path-style addressing
# against the account endpoint.
#
# R2_PUBLIC_DOMAIN is the hostname the browser fetches from - either the
# bucket's r2.dev subdomain or a custom domain on Cloudflare. Without it the
# API would hand out signed, expiring URLs, which is wrong for a public
# catalogue.

R2_BUCKET = env('R2_BUCKET')
R2_ACCOUNT_ID = env('R2_ACCOUNT_ID')
R2_ACCESS_KEY_ID = env('R2_ACCESS_KEY_ID')
R2_SECRET_ACCESS_KEY = env('R2_SECRET_ACCESS_KEY')
R2_PUBLIC_DOMAIN = env('R2_PUBLIC_DOMAIN')

USE_R2 = all([R2_BUCKET, R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY])

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

if USE_R2:
    DEFAULT_FILE_STORAGE_CONFIG = {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {
            'bucket_name': R2_BUCKET,
            'endpoint_url': 'https://{}.r2.cloudflarestorage.com'.format(
                R2_ACCOUNT_ID
            ),
            'access_key': R2_ACCESS_KEY_ID,
            'secret_key': R2_SECRET_ACCESS_KEY,
            'region_name': 'auto',
            'signature_version': 's3v4',
            'addressing_style': 'path',
            # R2 has no ACL concept; the bucket itself is public.
            'default_acl': None,
            'querystring_auth': False,
            # Keep a re-upload from silently replacing a live product image.
            'file_overwrite': False,
            'custom_domain': R2_PUBLIC_DOMAIN or None,
            'object_parameters': {
                'CacheControl': 'public, max-age=31536000, immutable',
            },
        },
    }
else:
    DEFAULT_FILE_STORAGE_CONFIG = {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    }

STORAGES = {
    'default': DEFAULT_FILE_STORAGE_CONFIG,
    'staticfiles': {
        'BACKEND': (
            'whitenoise.storage.CompressedStaticFilesStorage'
            if DEBUG or TESTING
            else 'whitenoise.storage.CompressedManifestStaticFilesStorage'
        ),
    },
}


# Django REST Framework

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],
    'DEFAULT_PAGINATION_CLASS': 'products.pagination.ProductPagination',
    'PAGE_SIZE': 24,
}


# CORS - the React storefront

CORS_ALLOWED_ORIGINS = env_list(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://127.0.0.1:3000',
)


# Behind Railway's proxy, so trust its forwarded scheme.

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# Email

MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}
