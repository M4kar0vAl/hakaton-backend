import sys
from datetime import timedelta
from pathlib import Path

try:
    from .local_settings import *
except ImportError:
    from .prod_settings import *

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY')

DEBUG = os.getenv('DEBUG') == 'True'

ALLOWED_HOSTS = ['.localhost', '127.0.0.1', '[::1]', 'w2w-backend.onrender.com']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # library
    'drf_spectacular',
    'rest_framework',
    'rest_framework_simplejwt',
    'cities_light',
    'tinymce',

    # apps
    'core.apps.accounts.apps.AccountsConfig',
    'core.apps.brand.apps.BrandConfig',
    'core.apps.payments.apps.PaymentsConfig',
    'core.apps.chat.apps.ChatConfig',
    'core.apps.analytics.apps.AnalyticsConfig',
    'core.apps.cities.apps.CitiesConfig',
    'core.apps.blacklist.apps.BlacklistConfig',
    'core.apps.articles.apps.ArticlesConfig',

    # should be last
    'django_cleanup.apps.CleanupConfig',
]

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

ROOT_URLCONF = 'core.config.urls'
CHANNELS_URLCONF = 'core.apps.chat.routing'

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

# speeds up tests by approximately 5 times
if 'test' in sys.argv:
    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]

PASSWORD_RESET_TIMEOUT = 86400  # 1 day in seconds

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10Mb
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5Mb

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTHENTICATION_BACKENDS = (
    'core.apps.accounts.backend.AuthBackend',  # кастомный бекэнд аутентификации
    'django.contrib.auth.backends.ModelBackend',  # для входа в админ панель
)

# DRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FileUploadParser',
    ],
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
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
        'core.apps.accounts.schema.user_me_postprocessing_hook',
        'core.apps.brand.schema.brand_me_postprocessing_hook',
        'drf_spectacular.hooks.postprocess_schema_enums',
    ],
}

# JWT tokens
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(weeks=4),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': False,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',

    'JTI_CLAIM': 'jti',
}

# channels
# For some reason it tries to connect to redis in tests sometimes, even if settings were overridden in test case
if 'test' in sys.argv:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [(os.getenv('REDIS_HOST'), os.getenv('REDIS_PORT'))],
            },
        },
    }

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_USE_SSL = False
EMAIL_USE_TLS = True
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
EMAIL_PORT = os.getenv('EMAIL_PORT')

# cities_light
CITIES_LIGHT_TRANSLATION_LANGUAGES = []
CITIES_LIGHT_INCLUDE_COUNTRIES = ['RU']
CITIES_LIGHT_INCLUDE_CITY_TYPES = ['PPL', 'PPLA', 'PPLA2', 'PPLA3', 'PPLA4', 'PPLC', 'PPLF', 'PPLL', 'PPLS', ]

# rabbitmq
RABBITMQ_USER = os.getenv('RABBITMQ_DEFAULT_USER')
RABBITMQ_PASS = os.getenv('RABBITMQ_DEFAULT_PASS')
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST')

# celery
CELERY_BROKER_URL = f'amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}:5672'

# TinyMCE
TINYMCE_EXTRA_MEDIA = {
    'js': [
        "tinymce/js/filePicker.js",
        "tinymce/js/editorSetupCallback.js",
        "tinymce/js/imageUploadHandler.js",
    ],
}

TINYMCE_DEFAULT_CONFIG = {
    "theme": "silver",
    "promotion": False,
    "height": 500,
    "menu": {
        "file": {
            "title": 'File',
            "items": 'newdocument restoredraft | preview | print'
        },
        "edit": {
            "title": 'Edit',
            "items": 'undo redo | cut copy paste pastetext | selectall | searchreplace'
        },
        "view": {
            "title": 'View',
            "items": 'code | visualaid visualblocks | preview fullscreen'
        },
        "insert": {
            "title": 'Insert',
            "items": 'image media link inserttable accordion | charmap emoticons hr | '
                     'pagebreak nonbreaking anchor | insertdatetime'
        },
        "format": {
            "title": 'Format',
            "items": 'bold italic underline strikethrough superscript subscript codeformat | '
                     'styles blocks fontfamily fontsize align lineheight | forecolor backcolor | removeformat'
        },
        "tools": {
            "title": 'Tools',
            "items": 'code wordcount'
        },
        "table": {
            "title": 'Table',
            "items": 'inserttable | cell row column | tableprops deletetable'
        },
        "help": {
            "title": 'Help',
            "items": 'help'
        }
    },
    "plugins": "advlist,autolink,lists,link,image,charmap,preview,anchor,"
               "searchreplace,visualblocks,code,fullscreen,insertdatetime,media,table,"
               "code,help,wordcount,emoticons,pagebreak,nonbreaking,accordion,autosave",
    "toolbar_mode": "sliding",
    "toolbar": "undo redo | fontfamily fontsize lineheight | bold italic underline backcolor forecolor | "
               "styles | bullist numlist outdent indent | removeformat | preview fullscreen",
    "insertdatetime_formats": ['%H:%M:%S', "%d.%m.%Y"],
    "skin": "oxide-dark",
    "file_picker_callback": 'filePicker',  # see core/static/tinymce/js/filePicker.js for code
    "images_upload_url": "/api/v1/tinymce/upload",
    "images_upload_handler": "imageUploadHandler",
    "relative_urls": False,
    "automatic_uploads": False,
    "media_alt_source": False,
    "setup": 'editorSetupCallback',  # see core/static/tinymce/js/editorSetupCallback.js for code
}

# common
ALLOWED_IMAGE_MIME_TYPES = [
    'image/gif', 'image/jpeg', 'image/pjpeg', 'image/png', 'image/webp', 'image/heic', 'image/avif'
]
ALLOWED_VIDEO_MIME_TYPES = [
    'video/mpeg', 'video/mp4', 'video/ogg', 'video/quicktime', 'video/webm', 'video/3gpp', 'video/3gpp2',
]
ALLOWED_AUDIO_MIME_TYPES = [
    'audio/mp4', 'audio/mpeg', 'audio/ogg', 'audio/webm', 'audio/flac', 'audio/x-flac', 'audio/3gpp', 'audio/3gpp2',
    'audio/x-ogg', 'audio/opus'
]

# chat app
# how much time an unlinked (message=None) attachment should stay on the server
MESSAGE_ATTACHMENT_DANGLING_LIFE_TIME = timedelta(minutes=10)
MESSAGE_ATTACHMENT_MAX_SIZE = 5242880  # 5Mb
MESSAGE_ATTACHMENT_ALLOWED_MIME_TYPES = ALLOWED_IMAGE_MIME_TYPES + ALLOWED_VIDEO_MIME_TYPES + ALLOWED_AUDIO_MIME_TYPES
