import magic


def is_valid_file_type(allowed_mime_types, file):
    file.seek(0)
    file_mime_type = magic.from_buffer(file.read(), mime=True)

    return file_mime_type in allowed_mime_types
