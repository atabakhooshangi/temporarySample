from abc import ABC, abstractmethod




class BasePaymentGatewayClient(ABC):

    @abstractmethod
    async def create_payment(self, *args, **kwargs):
        pass

    @abstractmethod
    async def verify_payment(self, *args, **kwargs):
        pass