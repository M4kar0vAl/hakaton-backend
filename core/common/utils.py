import uuid


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
