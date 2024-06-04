import os
from pathlib import Path

try:
    from .local_settings import *
except ImportError:
    from .prod_settings import *


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-!(usszats0h&5io)m_#7tf@^qou^jirw*waj1%f025cn&b)jm^'

DEBUG = os.getenv('DEBUG')

ALLOWED_HOSTS = []


INSTALLED_APPS = [
    "daphne",  # должен быть первым в списке, переопределяет команду runserver
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # library
    'drf_spectacular',
    'rest_framework',

    # apps
    'core.apps.accounts.apps.AccountsConfig',
    'core.apps.brand.apps.BrandConfig',
    'core.apps.chat.apps.ChatConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.config.urls'

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

WSGI_APPLICATION = 'core.config.wsgi.application'
ASGI_APPLICATION = 'core.config.asgi.application'

# модель пользователя
AUTH_USER_MODEL = 'accounts.User'

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


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


STATIC_URL = 'static/'

MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTHENTICATION_BACKENDS = (
    'core.apps.accounts.backend.AuthBackend',  # кастомный бекэнд аутентификации
    'django.contrib.auth.backends.ModelBackend',  # для входа в админ панель
)

#DRF
REST_FRAMEWORK = {
    # 'DEFAULT_AUTHENTICATION_CLASSES': (
    #     'rest_framework_simplejwt.authentication.JWTAuthentication',
    # ),
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'TEST_REQUEST_RENDERER_CLASSES': [
        'rest_framework.renderers.MultiPartRenderer',
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.TemplateHTMLRenderer',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',  # drf-spectacular
}

# spectacular
SPECTACULAR_SETTINGS = {
    'TITLE': 'Women to Women',
    'DESCRIPTION': 'API документация проекта W2W',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'POSTPROCESSING_HOOKS': [
        'drf_spectacular.hooks.postprocess_schema_enums',
    ],
}