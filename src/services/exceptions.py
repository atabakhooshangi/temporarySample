from rest_framework import status

from core.base_exception import BaseApiException
from core.message_text import MessageText


class ServiceIsNotFound(BaseApiException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = MessageText.ServiceIsNotFound404
    default_code = 404


class ServicePendingApplyIsNotValid(BaseApiException):
    status_code = status.HTTP_406_NOT_ACCEPTABLE
    default_detail = MessageText.CanNotPendingApplyOnThisService406
    default_code = 406


class ZibalPaymentGatewayException(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.ZibalPaymentGatewayError400
    default_code = 400


class ExPayPaymentGatewayException(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.ExPayPaymentGatewayError400
    default_code = 400


class ServiceSubscriptionFailedException(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.ServiceSubscriptionFailed400
    default_code = 400


class AlreadySubscribedException(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.AlreadySubscribed400
    default_code = 400


class AlreadyUsedTrialSubscriptionException(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.AlreadyUsedTrialSubscription400
    default_code = 400


class ServiceIsFreeException(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.ServiceIsFree400
    default_code = 400


class TrialNotAvailableException(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.TrialNotAvailable400
    default_code = 400


class AccountingSocialTransactionAPIException(BaseApiException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = MessageText.AccountingSocialTransactionSubmissionFailed500
    default_code = 500


class AccountingWalletBalanceDecrementAPIException(BaseApiException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = MessageText.AccountingWalletBalanceDecrementFailed500
    default_code = 500


class ServiceIsNotSupportTrialException(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.ServiceIsNotSupportTrial400
    default_code = 400


class UseSeriveTrialLimiteException(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.UseTrialLimit400
    default_code = 400


class UseThisServiceTrialException(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.UseServiceTrialOnce400
    default_code = 400


class AccountingWalletBalanceIsNotEnoughException(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.AccountingWalletBalanceIsNotEnough400
    default_code = 400


class CampaignNotFound(BaseApiException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = MessageText.CampaignNotFond404
    default_code = 404
