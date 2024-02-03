from rest_framework.generics import ListAPIView

from signals.models import CoinDecimalNumber
from signals.serializers.coin import DecimalNumberCoinSerializer
from rest_framework.permissions import AllowAny


class CoinDecimalNumberConfigView(
    ListAPIView
):

    queryset = CoinDecimalNumber.objects.all()
    serializer_class = DecimalNumberCoinSerializer
    permission_classes = [AllowAny]
    filter_fields = (
        'coin_pair',
    )
