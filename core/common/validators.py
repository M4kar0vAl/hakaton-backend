import magic
from django.conf import settings
from django.core.exceptions import ValidationError


def is_valid_file_type(allowed_mime_types, file):
    file.seek(0)
    file_mime_type = magic.from_buffer(file.read(), mime=True)

    return file_mime_type in allowed_mime_types


def is_valid_video(file):
    if not is_valid_file_type(settings.ALLOWED_VIDEO_MIME_TYPES, file):
        raise ValidationError('Unsupported video type!')


def is_valid_image(file):
    if not is_valid_file_type(settings.ALLOWED_IMAGE_MIME_TYPES, file):
        raise ValidationError('Unsupported image type!')
