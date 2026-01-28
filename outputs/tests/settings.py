import os

# Use PostgreSQL for testing (matches production environment)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'test_db'),
        'USER': os.environ.get('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'postgres'),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}

# Secret key for testing
SECRET_KEY = 'test-secret-key-for-django-outputs'

# Installed apps
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.sessions',
    'django.contrib.messages',
    'crispy_forms',
    'django_filters',
    'django_rq',
    'django_select2',  # Required for filters
    'pragmatic',
    'outputs',
]

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

# Templates
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

# RQ Configuration - use fake queue for testing
# Note: fakeredis is configured in conftest.py via monkeypatch
RQ_QUEUES = {
    'default': {
        'HOST': 'localhost',
        'PORT': 6379,
        'DB': 0,
        'PASSWORD': '',
        'DEFAULT_TIMEOUT': 360,
    },
    'cron': {
        'HOST': 'localhost',
        'PORT': 6379,
        'DB': 0,
        'PASSWORD': '',
        'DEFAULT_TIMEOUT': 360,
    },
    'exports': {
        'HOST': 'localhost',
        'PORT': 6379,
        'DB': 0,
        'PASSWORD': '',
        'DEFAULT_TIMEOUT': 360,
    },
}

# Media and static files
MEDIA_ROOT = os.path.join(os.path.dirname(__file__), 'media')
STATIC_ROOT = os.path.join(os.path.dirname(__file__), 'static')

# Language settings
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_TZ = True
SITE_ID = 1

DEFAULT_FROM_EMAIL = 'test@example.com'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Outputs settings
OUTPUTS_EXCLUDE_EXPORTERS = []
OUTPUTS_EXPORTERS_MODULE_MAPPING = {}
OUTPUTS_MIGRATION_DEPENDENCIES = []
OUTPUTS_RELATED_MODELS = []
OUTPUTS_NUMBER_OF_THREADS = 2
OUTPUTS_SAVE_AS_FILE = False

# Email backend for testing
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Enable migrations for tests to ensure proper schema creation
# PostgreSQL is now used, so migrations work correctly
MIGRATION_MODULES = {}

# Default permissions
DEFAULT_PERMISSIONS = ('add', 'change', 'delete', 'view')

# Crispy forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# URL configuration
ROOT_URLCONF = 'outputs.tests.urls'

