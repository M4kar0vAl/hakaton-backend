import os

import dj_database_url
from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv('DEBUG') == 'True'

if not DEBUG:
    DATABASES = {
        'default': dj_database_url.parse(os.getenv('DATABASE_URL'))
    }
