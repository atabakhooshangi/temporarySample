import json
from core.api_gateways import ProducerClientGateway, KafkaTopic


def send_sms(mobile_to: str, token: str, **kwargs) -> None:
    data = {
        "mobile_to": mobile_to,
        "info": token,
        **kwargs
    }
    ProducerClientGateway().produce(
        topic=KafkaTopic.SMS,
        message=json.dumps(data)
    )
    return
