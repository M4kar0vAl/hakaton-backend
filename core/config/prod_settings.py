import os

import dj_database_url
from django.conf import settings
from dotenv import load_dotenv

load_dotenv()

if not settings.DEBUG:
    DATABASES = {
        'default': dj_database_url.parse(os.getenv('DATABASE_URL'))
    }
