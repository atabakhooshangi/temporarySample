from rest_framework import status

from core.base_exception import BaseApiException
from core.message_text import MessageText


class UserProfileNotFound(BaseApiException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = MessageText.UserProfileIsNotFound404
    default_code = 404


class UserProfileIsExists(BaseApiException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = MessageText.UserProfileIsExists
    default_code = 409


class ServiceNotFound(BaseApiException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = MessageText.ServicesNotFound404
    default_code = 404


class ApiKeyExist(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.ApiKeyExist
    default_code = 400


class ChangeDefaultApiKeyImpossible(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.ApiKeyDefaultImpossible400
    default_code = 400
