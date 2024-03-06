import requests
import traceback

from django.conf import settings

from core.api_gateways import APICallResultType, HTTPMethod
from services.models import Service, Subscription
from user.models import Profile

class AccountingAPIClient:

    def __init__(
        self,
        # access_token: str,  # TODO impelment internal authorization
        accounting_base_url: str = settings.ACCOUNTING_URL
    ) -> None:
        # self.access_token = access_token  # TODO impelment internal authorization
        self.base_url = f"{accounting_base_url}{settings.API_V1_STR}"

    @property
    def bearer_authorization_header(self):
        return f"Bearer {self.access_token}"

    def _send_request(
            self,
            method: str,
            url: str,
            data: dict,
            headers: dict,
            *args,
            **kwargs
    ):
        try:
            accounting_response = requests.request(
                method=method,
                url=url,
                json=data,
                headers=headers,
                *args,
                **kwargs
            )
            json_data = accounting_response.json()
            if json_data.get("status_code") == 200:
                return dict(
                    result_type=APICallResultType.SUCCESSFUL,
                    data=json_data,
                    error_detail=None,
                )
            return dict(
                result_type=APICallResultType.API_ERROR,
                data=None,
                error_detail=json_data,
            )
        except Exception as exc:
            print("Exception while creating social transaction", exc.args)
            return dict(
                result_type=APICallResultType.EXCEPTION,
                data=None,
                error_detail=traceback.format_exc(),
            )

    def decrease_wallet_balance(self, data: dict, *args, **kwargs):
        return self._send_request(
            method=HTTPMethod.PUT.value,
            url=self.base_url + settings.ACCOUNTING_DECREASE_WALLET_BALANCE_ENDPOINT,
            data=data,
            headers={
                "X-test-API": settings.ACCOUNTING_API_KEY,
                "Content-Type": "application/json"
            }
        )

    def create_social_transaction(self, data: dict, *args, **kwargs):
        return self._send_request(
            method=HTTPMethod.POST.value,
            url=self.base_url + settings.ACCOUNTING_CREATE_SOCIAL_TRANSACTION_ENDPOINT,
            data=data,
            headers={
                # TODO impelment internal authorization
                # authorization=self.bearer_authorization_header,
                "Content-Type": "application/json"
            }
        )


class AccountingAPIRequestBodyGenerator:

    @staticmethod
    def decrease_wallet_balance(subscription: Subscription):
        service: Service = subscription.service
        subscriber: Profile = subscription.subscriber
        return dict(
            user_id=subscriber.owner_id,
            c_type=service.subscription_coin.lower(),
            amount=subscription.amount,
            reference_id=subscription.id,
            reference_type="social_crypto_subscription",
            order_type="withdraw",
        )

    @staticmethod
    def create_social_transaction(subscription: Subscription, discount_code=None):
        service: Service = subscription.service
        subscriber: Profile = subscription.subscriber
        total_income = subscription.amount
        platform_income = (
            total_income * service.platform_fee
        ) / 100
        vendor_income = total_income - platform_income
        return dict(
            subscription_date=str(subscription.created_at.date()),
            subscriber_id=subscriber.id,
            subscriber_owner_id=subscriber.owner_id,
            subscriber_username=subscriber.username,
            subscriber_title=subscriber.title,
            owner_id=service.profile.owner_id,
            vendor_id=service.profile.id,
            vendor_title=service.profile.title,
            service_id=service.id,
            service_title=service.title,
            vendor_income=vendor_income,
            platform_income=platform_income,
            total_income=total_income,
            discount_code=discount_code.code_string if discount_code else None,
        )
