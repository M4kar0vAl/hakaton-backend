import hashlib

from django.utils.crypto import get_random_string


def get_recovery_token():
    return get_random_string(22)


def get_recovery_token_hash(token: str):
    return hashlib.sha256(token.encode()).hexdigest()
