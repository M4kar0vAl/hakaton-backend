import os

import dj_database_url
from dotenv import load_dotenv

from core.common.utils import get_secret

load_dotenv()

DEBUG = os.getenv('DEBUG') == 'True'

if not DEBUG:
    DATABASES = {
        'default': dj_database_url.parse(os.getenv('DATABASE_URL'))
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': get_secret('DB_NAME'),
            'USER': get_secret('DB_USER'),
            'PASSWORD': get_secret('DB_PASS'),
            'HOST': os.getenv('DB_HOST'),
            'PORT': os.getenv('DB_PORT'),
        },
    }