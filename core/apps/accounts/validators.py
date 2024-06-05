import re

from rest_framework.exceptions import ValidationError


def phone_validator(phone: str) -> None:
    phone_pattern = re.compile(r'^\+7\d{10}$')
    if not phone_pattern.match(phone):
        raise ValidationError(
            'Некорректный номер телефона. Номер должен быть в формате "+79993332211"'
        )
