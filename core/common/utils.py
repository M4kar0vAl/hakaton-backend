import os
import uuid


def get_secret(key):
    value = os.getenv(key)

    if os.path.isfile(value):
        with open(value) as f:
            return f.read()

    return value


def get_file_extension(filename):
    """
    Get extension of a file in .ext format
    """
    return '.' + filename.split('.')[-1]


def get_random_filename_with_extension(filename):
    """
    Get a random filename and keep its extension.
    """
    return f'{uuid.uuid4()}{get_file_extension(filename)}'
