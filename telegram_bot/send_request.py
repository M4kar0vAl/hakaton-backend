import requests
from requests.models import Response


def set_telegram_id_django(user_id: str, telegram_id: int) -> Response:
    url = 'http://django:8000/auth/users/set_telegram_id/'
    response = requests.patch(
        url,
        data={'telegram_id': telegram_id, 'user_id': user_id},
    )
    return response

