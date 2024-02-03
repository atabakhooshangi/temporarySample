import logging
import requests

from django.conf import settings

logger = logging.getLogger(__name__)


class KafkaTopic:
    MESSAGE_TOPIC = "message"
    BULK_MESSAGE_TOPIC = "bulk_message"
    SMS = "sms"
    VENDOR_SMS = "vendor_sms"
    CIVIL_REGISTRY_CREDENTIAL_VALIDATION_TOPIC = "civil_registry_bank_account_validation"
    CIVIL_REGISTRY_BANK_ACCOUNT_VALIDATION_TOPIC = "civil_registry_credential_validation"


class ProducerClientGateway:
    def produce(self, topic, message):
        item = {'topic': topic, 'message': message}
        try:
            requests.post(
                url=f'{settings.PRODUCER_MANAGEMENT_URL}/',
                headers={
                    "Content-Type": "application/json",
                    "authorization": settings.SOCIAL_API_KEY
                },
                json=item
            )
        except Exception as exc:
            logger.exception("Kafka produce failed")