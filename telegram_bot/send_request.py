import requests
import jwt

from requests.models import Response
from .conf import BOT_URL, SECRET_KEY


def set_telegram_id_django(user_id: str, telegram_id: int) -> Response:
    url = 'http://django:8000/auth/users/set_telegram_id/'
    token = jwt.encode(
        {'bot': BOT_URL},
        SECRET_KEY,
        algorithm='HS256',
    )
    headers = {
        'X-Internal-Request': token
    }
    response = requests.patch(
        url,
        data={'telegram_id': telegram_id, 'user_id': user_id},
        headers=headers,
    )
    return response
