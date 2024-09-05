from rest_framework import status
from rest_framework.exceptions import APIException


class BadRequest(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Bad request'
    default_code = 'bad_request'


class ServerError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'Server Error'
    default_code = 'server_error'
