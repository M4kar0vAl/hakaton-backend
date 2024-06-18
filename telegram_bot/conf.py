import os

from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv('TOKEN')
BOT_URL = os.getenv('BOT_URL')
SECRET_KEY = os.getenv('SECRET_KEY')

REDIS_USER = os.getenv('REDIS_USER')
REDIS_PASS = os.getenv('REDIS_PASS')
REDIS_HOST = os.getenv('REDIS_HOST')
# REDIS_HOST = 'localhost'
REDIS_PORT = os.getenv('REDIS_PORT')
REDIS_BOT_DB = os.getenv('REDIS_BOT_DB')
