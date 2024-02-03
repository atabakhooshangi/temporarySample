import json

import requests
from django.conf import settings

from services.payment import BasePaymentGatewayClient

EXPAY_BASE_URL = settings.EXPAY_BASE_URL  # Required


class ExPayGatewayClient(BasePaymentGatewayClient):

    def create_payment(self,
                             amount: float,
                             sub_merchant_id: int,
                             callback_url: str,
                             ):
        request_data = {
            "currency": "TRON",
            "sub_merchant_id": sub_merchant_id,
            "amount": amount,
            "lock_offset": settings.CRYPTO_GATEWAY_LOCK_OFFSET
        }
        response = requests.post(
            url=EXPAY_BASE_URL + '/wallets/deposit-link-request/',
            data=json.dumps(request_data),
            headers={
                'Content-Type': 'application/json',
                'MERCHANT-KEY': settings.EXPAY_MERCHANT_KEY
            }
        )
        res = response.json()
        print("res", res, "status", response.status_code)
        if response.status_code == 200:
            return res
        else:
            raise InterruptedError('Error on crypto payment.')

    async def verify_payment(self, *args, **kwargs):
        pass
