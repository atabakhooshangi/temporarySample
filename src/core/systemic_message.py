import json

from typing import List


from core.choice_field_types import MessageCategoryChoices
from core.api_gateways import (
    ProducerClientGateway,
    KafkaTopic,
)


def send_systemic_message(
    message_category: MessageCategoryChoices,
    user_id: int,
    message_info: dict,
):
    """
    produce a send message event to kafka, 
    the consumer can fetch the data and send a
    systemic message based on the provided data
    """
    data = {
        'type': message_category,
        'user_id': user_id,
        'info': message_info,
    }
    ProducerClientGateway().produce(
        topic=KafkaTopic.MESSAGE_TOPIC,
        message=json.dumps(data)
    )


def send_bulk_systemic_message(
    message_category: MessageCategoryChoices,
    user_ids: List[int],
    message_info: dict,
):
    """
    produce a send message event to kafka, 
    the consumer can fetch the data and send bulk
    systemic message based on the provided data
    """
    data = {
        'type': message_category,
        'user_ids': user_ids,
        'info': message_info,
    }
    ProducerClientGateway().produce(
        topic=KafkaTopic.BULK_MESSAGE_TOPIC,
        message=json.dumps(data)
    )
