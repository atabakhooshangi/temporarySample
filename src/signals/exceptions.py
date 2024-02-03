from rest_framework import status

from core.base_exception import BaseApiException
from core.message_text import MessageText


class RequiredField(BaseApiException):
    status_code = status.HTTP_406_NOT_ACCEPTABLE
    default_detail = MessageText.RequiredField406
    default_code = 406


class UndeletableSignal(BaseApiException):
    status_code = status.HTTP_406_NOT_ACCEPTABLE
    default_detail = MessageText.UndeletableSignal406
    default_code = 406


class TradingSignalIsNotFound(BaseApiException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = MessageText.TradingSignalIsNotFound404
    default_code = 404


class UserProfileIsNotFound(BaseApiException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = MessageText.UserProfileIsNotFound404
    default_code = 404


class UserISNotVendor(BaseApiException):
    status_code = status.HTTP_406_NOT_ACCEPTABLE
    default_detail = MessageText.UserISNotVendor406
    default_code = 406


class ValueNumberIsNotValid(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 400


class ValueDataIsNotEditable(BaseApiException):
    status_code = status.HTTP_406_NOT_ACCEPTABLE
    default_detail = MessageText.ThisValueIsNotEditable
    default_code = 406


class NotSupportQuickCopySpotSignal(BaseApiException):
    status = status.HTTP_406_NOT_ACCEPTABLE
    default_detail = MessageText.NotSupportSpotSignal
    default_code = 406


class NotSupportQuickCopyThisSignal(BaseApiException):
    status = status.HTTP_406_NOT_ACCEPTABLE
    default_detail = MessageText.NotSupportThisSignal
    default_code = 406


class NotSupportSupportThisPairCoinExchagne(BaseApiException):
    status = status.HTTP_406_NOT_ACCEPTABLE
    default_detail = MessageText.NotSupportThisExchagePairCoin
    default_code = 406


class SignalIsCopiedOnce(BaseApiException):
    status = status.HTTP_406_NOT_ACCEPTABLE
    default_detail = MessageText.SignalIsCopiedOnce
    default_code = 406


class OrderIsNotFound(BaseApiException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = MessageText.OrderIsNotExist404
    default_code = 404


class NotEnoughSignalBalance(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.NotEnoughVirtualBalance
    default_code = 400


class PositionDoesNotHaveOrder(BaseApiException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = MessageText.OrderOFPositionIsNotExist404
    default_code = 400
