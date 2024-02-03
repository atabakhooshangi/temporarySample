from rest_framework import serializers

from signals.models import CoinDecimalNumber


class DecimalNumberCoinSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    coin_pair = serializers.CharField()
    decimal_num = serializers.IntegerField()

    class Meta:
        fields = (
            'id',
            'coin_pair',
            'decimal_num',
        )
        readonly_fields = fields
