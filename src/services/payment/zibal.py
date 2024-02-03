import json
import traceback
import logging
import requests


from django.conf import settings

from core.api_gateways.base import APICallResultType
from services.payment import BasePaymentGatewayClient


logger = logging.getLogger(__name__)

ZIBAL_PAYMENT_BASE_URL = settings.ZIBAL_PAYMENT_BASE_URL
ZIBAL_BASE_URL = settings.ZIBAL_BASE_URL  # Required


class ZibalGatewayClient(BasePaymentGatewayClient):
    create_code_mapper = {
        100: "با موفقیت تایید شد.",
        102: "merchant یافت نشد.",
        103: "Mamerchant غیرفعالrch",
        104: "merchant نامعتبر",
        201: "قبلا تایید شده.",
        105: "amount بایستی بزرگتر از 1,000 ریال باشد.",
        106: "callbackUrl نامعتبر می‌باشد. (شروع با http و یا https)",
        113: "amount مبلغ تراکنش از سقف میزان تراکنش بیشتر است.",
    }

    verify_code_mapper = {
        100: "با موفقیت تایید شد.",
        102: "merchant یافت نشد.",
        103: "merchant غیر فعال",
        104: "merchant نامعتبر",
        201: "قبلا تایید شده.",
        202: "سفارش پرداخت نشده یا ناموفق بوده است.",
        203: "trackId نامعتبر می‌باشد.",
    }

    def create_payment(
        self,
        amount: int,
        callback_url: str,
        description: str = "",
    ):
        try:
            request_data = dict(
                merchant=settings.ZIBAL_MERCHANT_ID,
                amount=amount,
                callbackUrl=callback_url,
                description=description,
            )
            response = requests.post(
                url=ZIBAL_BASE_URL + 'request',
                data=json.dumps(request_data),
                headers={'Content-Type': 'application/json'}
            )
            json_response = response.json()
            result = json_response["result"]
            if result == 100:
                return dict(
                    result_type=APICallResultType.SUCCESSFUL,
                    data=json_response,
                    error_detail=None,
                )
            return dict(
                result_type=APICallResultType.API_ERROR,
                data=json_response,
                error_detail=self.create_code_mapper.get(result),
            )
        except Exception as exc:
            return dict(
                result_type=APICallResultType.EXCEPTION,
                data=None,
                error_detail=traceback.format_exc(),
            )

    def verify_payment(
        self,
        ipg_track_id: str
    ):
        try:
            request_data = dict(
                merchant=settings.ZIBAL_MERCHANT_ID,
                trackId=ipg_track_id,
            )
            response = requests.post(
                url=ZIBAL_BASE_URL + 'verify',
                data=json.dumps(request_data),
                headers={'Content-Type': 'application/json'}
            )
            json_response = response.json()
            result = json_response["result"]
            if result == 100:
                return dict(
                    result_type=APICallResultType.SUCCESSFUL,
                    data=json_response,
                    error_detail=None,
                )
            return dict(
                result_type=APICallResultType.API_ERROR,
                data=json_response,
                error_detail=self.create_code_mapper.get(result),
            )
        except Exception as exc:
            return dict(
                result_type=APICallResultType.EXCEPTION,
                data=None,
                error_detail=traceback.format_exc(),
            )