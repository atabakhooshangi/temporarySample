import json

from django.utils.encoding import force_str
from rest_framework.exceptions import APIException, _get_error_details
from rest_framework import status

from core.message_text import MessageText


class BaseApiException(APIException):
    """
    for raising Exception define your exception with this structure:
        class SampleException(BaseApiException):
            status_code = status.HTTPStatusCode
            default_detail = error message
            default_code = code
    """

    def __init__(self, detail=None, code=None):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code
        self.detail = {
            'code': code,
            'detail': force_str(detail)
        }


class CustomValidationError(BaseApiException):
    pass


class LevelOneAuthenticationRequiredException(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = MessageText.LevelOneAuthenticationRequired403
    default_code = 403


class LevelTwoAuthenticationRequiredException(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = MessageText.LevelTwoAuthenticationRequired403
    default_code = 403


class DataNotExistException(BaseApiException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = MessageText.SettingDataNotFond404
    default_code = 404
