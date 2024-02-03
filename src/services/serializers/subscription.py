import json
import logging
from datetime import datetime, timedelta

from rest_framework import serializers
from rest_framework.reverse import reverse
from rest_framework.generics import get_object_or_404
from core.api_gateways import AccountingAPIClient, ProducerClientGateway, KafkaTopic
from django.db import transaction
from django.conf import settings

from core.api_gateways import (
    AccountingAPIClient,
    AccountingAPIRequestBodyGenerator
)
from core.choice_field_types import (
    MessageCategoryChoices,
    SubscriptionInvoiceStatusChoices,
    SubscriptionPaymentTypeChoices,
    ServiceTypeChoices,
)
from core.systemic_message import send_systemic_message
from invitation.models.invitation_code import InvitationTypeChoices
from services.exceptions import (
    AccountingSocialTransactionAPIException,
    ZibalPaymentGatewayException,
    AccountingWalletBalanceDecrementAPIException,
    TrialNotAvailableException,
    ServiceIsFreeException,
    ServiceIsNotSupportTrialException,
    ExPayPaymentGatewayException,
    AccountingWalletBalanceIsNotEnoughException
)
from services.models import Service, SubscriptionInvoice, Subscription
from services.payment import ZibalGatewayClient, APICallResultType
from copytrading.models import CopySetting
from services.payment.expay import ExPayGatewayClient
from services.serializers import ServiceMinimalReadOnlySerializer
from user.models import Profile
from user.serializers import ProfileMinimalReadOnlySerializer
from invitation.models import InviteBonus, InvitationCode

logger = logging.getLogger(__name__)


class SubscriptionMinimalReadOnlySerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = (
            "id",
            "payment_type",
            "service",
            "subscriber",
            "created_at",
        )


class InvoiceMinimalReadOnlySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionInvoice
        fields = (
            "id",
            "amount",
            "irt_amount",
            "usdt_amount",
            "reference_id"
        )


# SubscriberBriefinfoReadOnlySerializer
class SubscriberDetailReadOnlySerializer(serializers.ModelSerializer):
    subscriber = ProfileMinimalReadOnlySerializer(read_only=True)
    service = ServiceMinimalReadOnlySerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = (
            'id',
            'subscriber',
            'service',
            'payment_type',

        )


class SubscriptionReadOnlySerializer(serializers.ModelSerializer):
    service_title = serializers.CharField(read_only=True)
    service_type = serializers.CharField(read_only=True)
    successful_invoice = serializers.SerializerMethodField()
    subscriber = ProfileMinimalReadOnlySerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = (
            "id",
            "payment_type",
            "service_title",
            "service_type",
            "subscriber",
            "start_time",
            "expire_time",
            "amount",
            "is_paid",
            "created_at",
            "updated_at",
            "tracking_code",
            "successful_invoice"
        )

    def get_successful_invoice(self, obj):
        try:
            return InvoiceMinimalReadOnlySerializer(obj.successful_invoice[0]).data
        except:
            return


class ServiceSubscribeSerializer(serializers.Serializer):
    client_redirect_url = serializers.CharField(
        required=False,
        allow_null=True
    )
    payment_type = serializers.ChoiceField(
        choices=SubscriptionPaymentTypeChoices.choices,
        required=True,
        allow_null=False
    )
    code = serializers.CharField(
        required=False,
        allow_null=True
    )

    def make_trial_subscription(
            self,
            service: Service,
            subscriber: Profile
    ):
        if not service.has_trial:
            raise ServiceIsNotSupportTrialException
        subscription = Subscription.factory.get_or_create_trial(
            service=service,
            subscriber=subscriber
        )
        return subscription

    def make_crypto_gateway_paid_subscription(
            self,
            service: Service,
            subscriber: Profile,
            client_redirect_url: str,
            code: InvitationCode = None
    ):
        with transaction.atomic():
            previous_usdt_amount = None
            usdt_amount = service.subscription_fee
            if code:
                previous_usdt_amount = service.subscription_fee
                calculation_state, message, usdt_amount, irt_amount = code.calculate_final_price(service)
                if not calculation_state:
                    raise serializers.ValidationError(message)
            callback_url = self.context["request"].build_absolute_uri(
                reverse("invoice_verify")
            )
            start_time, expire_time = Subscription.objects.new_subscription_datetimes(
                service_id=service.id,
                subscriber_id=subscriber.id
            )
            if usdt_amount != 0:
                gateway_client = ExPayGatewayClient()
                payment_create_result = gateway_client.create_payment(
                    amount=float(usdt_amount),
                    callback_url=callback_url,
                    sub_merchant_id=int(client_redirect_url.split('/')[-1:][0])
                )
            else:
                payment_create_result = dict(
                    result_type=APICallResultType.SUCCESSFUL.value,
                    data="0"
                )
                send_systemic_message(
                    MessageCategoryChoices.SOCIAL_SERVICE_SUBSCRIPTION,
                    service.profile.owner_id,
                    dict(subscriber=subscriber.title)
                )
                ProducerClientGateway().produce(
                    topic=KafkaTopic.VENDOR_SMS,
                    message=json.dumps({
                        "owner_id": service.profile.owner_id,
                        "template": 'vendor-subscription'
                    })
                )
            invoice: SubscriptionInvoice = SubscriptionInvoice.objects.create(
                profile=subscriber,
                amount=usdt_amount,
                usdt_amount=usdt_amount,
                previous_amount=previous_usdt_amount,
                previous_usdt_amount=previous_usdt_amount,
                status=SubscriptionInvoiceStatusChoices.PENDING if usdt_amount != 0
                else SubscriptionInvoiceStatusChoices.SUCCESSFUL
            )
            # if not payment_create_result["result_type"] == APICallResultType.SUCCESSFUL:
            additional_data = dict(
                callback_url=callback_url,
                client_redirect_url=client_redirect_url,
                ipg_create_payment=dict(
                    response=payment_create_result["data"],
                    error_detail=payment_create_result.get("error"),
                )
            )
            invoice.additional_data = additional_data
            invoice.save()
            # raise ExPayPaymentGatewayException

            ipg_track_id = payment_create_result["data"]
            payment_url = settings.EXPAY_PAYMENT_URL + str(ipg_track_id)
            additional_data = dict(
                callback_url=callback_url,
                client_redirect_url=client_redirect_url,
                payment_url=payment_url,
                ipg_create_payment=dict(
                    response=payment_create_result,
                ),
            )
            pending_subscription = Subscription.objects.get_pending_subscription(
                service_id=service.id,
                subscriber_id=subscriber.id
            )
            if pending_subscription is None:
                if usdt_amount != 0:
                    pending_subscription = Subscription.factory.create_unpaid(
                        service=service,
                        subscriber=subscriber,
                        payment_type=SubscriptionPaymentTypeChoices.CRYPTO_GATEWAY_PAID,
                        invitation_code=code,
                        previous_amount=previous_usdt_amount,
                        discount_applied=True if code else False,
                        amount=usdt_amount
                    )
                else:
                    pending_subscription = Subscription.factory.create_paid(
                        service=service,
                        subscriber=subscriber,
                        payment_type=SubscriptionPaymentTypeChoices.CRYPTO_GATEWAY_PAID,
                        invitation_code=code,
                        previous_amount=previous_usdt_amount,
                        discount_applied=True if code else False,
                        amount=usdt_amount
                    )
                    start_time, expire_time = Subscription.objects.new_subscription_datetimes(
                        service_id=pending_subscription.service.id,
                        subscriber_id=pending_subscription.subscriber.id
                    )
                    pending_subscription.start_time = start_time
                    pending_subscription.expire_time = expire_time
                    pending_subscription.is_paid = True
            if code:
                code.used_count += 1
                code.save()
            pending_subscription.discount_applied = True if code else False
            pending_subscription.invitation_code = code
            pending_subscription.previous_amount = previous_usdt_amount
            pending_subscription.amount = usdt_amount
            pending_subscription.payment_type = SubscriptionPaymentTypeChoices.CRYPTO_GATEWAY_PAID
            pending_subscription.save()
            invoice.subscription = pending_subscription
            invoice.ipg_track_id = ipg_track_id
            invoice.additional_data = additional_data
            invoice.save()
        try:
            InviteBonus.objects.create(subscriber_iam_id=subscriber.owner_id)
        except Exception as e:
            print(e)
        return pending_subscription

    def make_crypto_internal_paid_subscription(
            self,
            service: Service,
            subscriber: Profile,
            code: InvitationCode = None
    ):
        with transaction.atomic():
            previous_usdt_amount = None
            usdt_amount = service.subscription_fee
            if code:
                previous_usdt_amount = service.subscription_fee
                calculation_state, message, usdt_amount, irt_amount = code.calculate_final_price(service)
                if not calculation_state:
                    raise serializers.ValidationError(message)
            start_time, expire_time = Subscription.objects.new_subscription_datetimes(
                service_id=service.id,
                subscriber_id=subscriber.id
            )
            subscription = Subscription.factory.create_paid(
                service=service,
                subscriber=subscriber,
                payment_type=SubscriptionPaymentTypeChoices.CRYPTO_INTERNAL_PAID,
                start_time=start_time,
                expire_time=expire_time,
                amount=usdt_amount,
                previous_amount=previous_usdt_amount,
                discount_applied=True if code else False,
                invitation_code=code,
            )
            # FIXME: merge the both api call in one crypto social transaction create
            # for keeping consistency and atomicity of flow
            accounting_api_client = AccountingAPIClient()
            response_data = accounting_api_client.create_social_transaction(
                data=AccountingAPIRequestBodyGenerator.create_social_transaction(
                    subscription=subscription,
                    discount_code=code if code else None
                )
            )
            if not response_data["result_type"] == APICallResultType.SUCCESSFUL:
                logger.error(response_data["error_detail"])
                raise AccountingSocialTransactionAPIException

            response_data = accounting_api_client.decrease_wallet_balance(
                data=AccountingAPIRequestBodyGenerator.decrease_wallet_balance(
                    subscription=subscription
                )
            )
            if not response_data["result_type"] == APICallResultType.SUCCESSFUL:
                if response_data["error_detail"]["status_code"] == 6001:
                    raise AccountingWalletBalanceIsNotEnoughException
                logger.error(response_data["error_detail"])
                raise AccountingWalletBalanceDecrementAPIException
            if code:
                code.used_count += 1
                code.save()
        try:
            InviteBonus.objects.create(subscriber_iam_id=subscriber.owner_id)
        except Exception as e:
            print(e)
        send_systemic_message(
            MessageCategoryChoices.SOCIAL_SERVICE_SUBSCRIPTION,
            subscription.service.profile.owner_id,
            dict(subscriber=subscription.subscriber.title)
        )
        ProducerClientGateway().produce(
            topic=KafkaTopic.VENDOR_SMS,
            message=json.dumps({
                "owner_id": service.profile.owner_id,
                "template": 'vendor-subscription'
            })
        )
        return subscription

    def make_irt_paid_subscription(
            self,
            service: Service,
            subscriber: Profile,
            subscription_amount: float,
            client_redirect_url: str,
            code: InvitationCode = None
    ):
        previous_irt_amount = None
        previous_usdt_amount = None
        usdt_subscription_amount = service.subscription_fee
        if code:
            previous_subscription_fee = subscription_amount
            previous_usdt_amount = service.subscription_fee
            calculation_state, message, usdt_amount, irt_amount = code.calculate_final_price(service,
                                                                                             do_irt_calculate=True)
            if not calculation_state:
                raise serializers.ValidationError(message)
            subscription_amount = irt_amount
            usdt_subscription_amount = usdt_amount
        callback_url = self.context["request"].build_absolute_uri(
            reverse("invoice_verify")
        )
        gateway_client = ZibalGatewayClient()
        payment_create_result = gateway_client.create_payment(
            amount=int(subscription_amount),
            callback_url=callback_url,
            description="خرید سابسکریپشن سرویس",
        )
        invoice: SubscriptionInvoice = SubscriptionInvoice.objects.create(
            profile=subscriber,
            amount=subscription_amount,
            usdt_amount=usdt_subscription_amount,
            previous_amount=previous_irt_amount,
            previous_usdt_amount=previous_usdt_amount
        )
        if not payment_create_result["result_type"] == APICallResultType.SUCCESSFUL:
            additional_data = dict(
                callback_url=callback_url,
                client_redirect_url=client_redirect_url,
                ipg_create_payment=dict(
                    response=payment_create_result["data"],
                    error_detail=payment_create_result["error_detail"],
                )
            )
            invoice.additional_data = additional_data
            invoice.save()
            raise ZibalPaymentGatewayException

        ipg_track_id = payment_create_result["data"]["trackId"]
        payment_url = f"{settings.ZIBAL_PAYMENT_BASE_URL}/{ipg_track_id}"
        additional_data = dict(
            callback_url=callback_url,
            client_redirect_url=client_redirect_url,
            payment_url=payment_url,
            ipg_create_payment=dict(
                response=payment_create_result["data"],
            ),
        )
        pending_subscription = Subscription.objects.get_pending_subscription(
            service_id=service.id,
            subscriber_id=subscriber.id
        )
        if pending_subscription is None:
            pending_subscription = Subscription.factory.create_unpaid(
                service=service,
                subscriber=subscriber,
                payment_type=SubscriptionPaymentTypeChoices.IRT_PAID,
                invitation_code=code,
                previous_amount=previous_usdt_amount,
                discount_applied=True if code else False,
                amount=usdt_subscription_amount
            )
        if code:
            code.used_count += 1
            code.save()
        pending_subscription.discount_applied = True if code else False
        pending_subscription.invitation_code = code
        pending_subscription.previous_amount = previous_usdt_amount
        pending_subscription.amount = usdt_subscription_amount
        payment_type = SubscriptionPaymentTypeChoices.IRT_PAID
        pending_subscription.save()
        invoice.subscription = pending_subscription
        invoice.ipg_track_id = ipg_track_id
        invoice.additional_data = additional_data
        invoice.save()
        return pending_subscription

    def update(
            self,
            service: Service,
            validated_data: dict
    ) -> Subscription:
        subscriber: Profile = validated_data["profile"]
        payment_type = validated_data["payment_type"]
        code = validated_data.get("code")
        # calculate the subscription price in toman(using an api call to wallex api
        # and get the tether toman price)
        subscription_amount = service.irt_subscription_price * 10
        if subscription_amount == 0:  # if the subscripttion amount is zero the service is free
            raise ServiceIsFreeException

        # check if the provided code is valid and the service is available for this code
        if code:
            code = get_object_or_404(
                InvitationCode.objects.all(),
                code_string=code,
            )
        # based on the provided payment type parameter choose the subscription type and
        # payment handling
        if payment_type == SubscriptionPaymentTypeChoices.TRIAL:
            if not service.has_trial:
                raise TrialNotAvailableException
            subscription: Subscription = self.make_trial_subscription(
                service=service,
                subscriber=subscriber
            )
        elif payment_type == SubscriptionPaymentTypeChoices.CRYPTO_GATEWAY_PAID:
            subscription: Subscription = self.make_crypto_gateway_paid_subscription(
                service=service,
                subscriber=subscriber,
                client_redirect_url=validated_data["client_redirect_url"],
                code=code
            )
        elif payment_type == SubscriptionPaymentTypeChoices.CRYPTO_INTERNAL_PAID:
            subscription: Subscription = self.make_crypto_internal_paid_subscription(
                service=service,
                subscriber=subscriber,
                # client_redirect_url=validated_data["client_redirect_url"],
                code=code
            )
        elif payment_type == SubscriptionPaymentTypeChoices.IRT_PAID:
            subscription: Subscription = self.make_irt_paid_subscription(
                service=service,
                subscriber=subscriber,
                subscription_amount=subscription_amount,
                client_redirect_url=validated_data["client_redirect_url"],
                code=code
            )

        # after subscribing a copy service a default settings for this user must
        # be generated on this service
        if subscription.service.service_type == ServiceTypeChoices.COPY:
            CopySetting.objects.update_or_create(
                service=subscription.service,
                profile=subscription.subscriber,
                defaults=dict(margin=settings.DEFAULT_COPY_MARGIN, )
            )
        return subscription


class IPGVerifyInvoiceSerializer(serializers.Serializer):
    ipg_track_id = serializers.CharField(allow_null=False, allow_blank=False)
    crypto_gateway = serializers.BooleanField(allow_null=True)
    status = serializers.BooleanField(allow_null=True)

    def create(self, validated_data):
        with transaction.atomic():
            ipg_track_id = validated_data["ipg_track_id"]
            invoice = get_object_or_404(
                SubscriptionInvoice.objects.all().select_related(
                    "subscription",
                    "subscription__subscriber",
                    "subscription__service",
                    "subscription__service__profile",
                ),
                ipg_track_id=ipg_track_id
            )
            if validated_data["crypto_gateway"]:
                invoice.status = SubscriptionInvoiceStatusChoices.SUCCESSFUL if validated_data["status"] \
                    else SubscriptionInvoiceStatusChoices.FAILED
                if validated_data["status"]:
                    subscription: Subscription = invoice.subscription
                    start_time, expire_time = Subscription.objects.new_subscription_datetimes(
                        service_id=subscription.service.id,
                        subscriber_id=subscription.subscriber.id
                    )
                    subscription.start_time = start_time
                    subscription.expire_time = expire_time
                    subscription.is_paid = True
                    subscription.save()
                    invoice.save()
                return invoice
            gateway_client = ZibalGatewayClient()
            payment_verify_result = gateway_client.verify_payment(
                ipg_track_id=ipg_track_id,
            )
            if not payment_verify_result["result_type"] == APICallResultType.SUCCESSFUL:
                invoice.status = SubscriptionInvoiceStatusChoices.FAILED
                invoice.additional_data["ipg_verify_payment"] = dict(
                    response=payment_verify_result["data"],
                    error_detail=payment_verify_result["error_detail"],
                )
                invoice.save()
                if payment_verify_result["data"]["result"] in (201, 202):
                    return invoice
                raise ZibalPaymentGatewayException

            invoice.status = SubscriptionInvoiceStatusChoices.SUCCESSFUL
            invoice.reference_id = payment_verify_result["data"]["refNumber"]
            invoice.additional_data["ipg_verify_payment"] = dict(
                response=payment_verify_result["data"],
            )
            subscription: Subscription = invoice.subscription
            start_time, expire_time = Subscription.objects.new_subscription_datetimes(
                service_id=subscription.service.id,
                subscriber_id=subscription.subscriber.id
            )
            subscription.start_time = start_time
            subscription.expire_time = expire_time
            subscription.is_paid = True
            subscription.save()
            # call the accounting social transaction api to submit the
            # social transaction record
            accounting_api_client = AccountingAPIClient()
            response_data = accounting_api_client.create_social_transaction(
                data=AccountingAPIRequestBodyGenerator.create_social_transaction(
                    subscription=subscription,
                    discount_code=subscription.invitation_code if subscription.discount_applied else None
                )
            )
            if not response_data["result_type"] == APICallResultType.SUCCESSFUL:
                logger.error(response_data["error_detail"])
                raise AccountingSocialTransactionAPIException
            ProducerClientGateway().produce(
                topic=KafkaTopic.VENDOR_SMS,
                message=json.dumps({
                    "owner_id": subscription.service.profile.owner_id,
                    "template": 'vendor-subscription'
                })
            )
            send_systemic_message(
                MessageCategoryChoices.SOCIAL_SERVICE_SUBSCRIPTION,
                invoice.subscription.service.profile.owner_id,
                dict(subscriber=invoice.subscription.subscriber.title)
            )
            invoice.save()
        try:
            InviteBonus.objects.create(subscriber_iam_id=subscription.subscriber.owner_id)
        except Exception as e:
            print(e)
        return invoice


class InvoiceReadOnlySerializer(serializers.ModelSerializer):
    profile = ProfileMinimalReadOnlySerializer(read_only=True)
    subscription = SubscriptionReadOnlySerializer(read_only=True)
    service_owner = serializers.SerializerMethodField()
    service_type = serializers.CharField(read_only=True)

    class Meta:
        model = SubscriptionInvoice
        fields = (
            "id",
            "profile",
            "service_type",
            "subscription",
            "service_owner",
            "usdt_amount",
            "amount",
            "description",
            "reference_id",
            "status",
            "created_at",
        )

    def get_service_owner(self, obj):
        return ProfileMinimalReadOnlySerializer(
            obj.subscription.service.profile
        ).data
