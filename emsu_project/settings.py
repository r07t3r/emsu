import os
from pathlib import Path
import environ
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(
    DEBUG=(bool, False)
)

environ.Env.read_env(os.path.join(BASE_DIR, '.env'))


# ──── SECURITY ──────────────────────────────────────────────────────────
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# ──── APPLICATION CONFIGURATION ──────────────────────────────────────────
AUTH_USER_MODEL = 'core.User'

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'channels',
    'core',
    'rest_framework',
    'authentication',
    'rest_framework_simplejwt',
]
SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ──── DATABASE ──────────────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME':     env('DB_NAME'),
        'USER':     env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST':     env('DB_HOST'),
        'PORT':     env('DB_PORT'),
        'OPTIONS':  {'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"},
    }
}

# ──── EMAIL ─────────────────────────────────────────────────────────────
EMAIL_BACKEND      = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST         = 'smtp.gmail.com'
EMAIL_PORT         = 587
EMAIL_USE_TLS      = True
EMAIL_HOST_USER    = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD= env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


# ──── REST FRAMEWORK ─────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 20,
}

ROOT_URLCONF = 'emsu_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'emsu_project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases


# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-gb'

TIME_ZONE = 'Africa/Lagos'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

# ──── STATIC ─────────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# for Whitenoise
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'
# ──── DEFAULT AUTO FIELD ─────────────────────────────────────────────────

# https://docs.djangoproject.com/en/3.2/ref/settings/#default-file-storage
# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'




ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_SUBJECT_PREFIX = '[EMSU] '

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

# === SMS (Africa’s Talking) ===
AFRICASTALKING_USERNAME = os.getenv('AT_USERNAME')
AFRICASTALKING_API_KEY   = os.getenv('AT_API_KEY')
AFRICASTALKING_SENDER    = os.getenv('AT_SENDER')   # e.g. "EMSU"

# ──── CHANNELS & CACHING ─────────────────────────────────────────────────
ASGI_APPLICATION = 'emsu_project.asgi.application'
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': { 'hosts': [env('REDIS_URL')] },
    },
}
# you can also use REDIS_URL for Django cache
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL'),
        'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
    }
}
