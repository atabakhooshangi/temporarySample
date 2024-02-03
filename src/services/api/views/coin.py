from rest_framework.mixins import (
    ListModelMixin,
    RetrieveModelMixin,
)
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import GenericViewSet

from signals.models import ExchangeMarket
from signals.serializers.signal import ExchangeMarketCoinReadOnlyModelSerializer


class CoinModelViewSet(
    GenericViewSet,
    ListModelMixin,
    RetrieveModelMixin
):
    queryset = ExchangeMarket.objects.all().distinct('base_currency')
    serializer_class = ExchangeMarketCoinReadOnlyModelSerializer
    search_fields = (
        'base_currency',
    )
    ordering_fields = (
        'base_currency'
    )
    permission_classes = [AllowAny]
