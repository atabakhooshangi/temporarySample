from django.conf import settings
from django_redis import get_redis_connection
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.views import APIView

from copytrading.exceptions import ApiKeyNotSetException
from copytrading.exchange import generate_exchange_client
from copytrading.models import ApiKey
from user.models import Profile


class ExchangeBalanceAPIView(APIView):
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'api_key_id',
                openapi.IN_QUERY,
                description="Api key id",
                type=openapi.TYPE_NUMBER
            ),
            openapi.Parameter(
                'trade_type',
                openapi.IN_QUERY,
                description='If the spot or future parameter is not provided, the default will be set to future',
                type=openapi.TYPE_STRING
            )
        ]
    )
    def get(self, request, *args, **kwargs):
        exchange = kwargs["exchange"]
        coin = kwargs["coin"]
        api_key_id = request.query_params.get('api_key_id', None)
        trade_type = request.query_params.get('trade_type', None)
        profile = get_object_or_404(Profile, owner_id=request.user.owner_id)
        upper_exchange = exchange.upper()
        trade_type = trade_type.lower() if trade_type is not None else None
        try:
            if api_key_id is None:
                api_key = ApiKey.objects.get(exchange=upper_exchange, owner=profile, is_default=True)
            else:
                api_key = ApiKey.objects.get(exchange=upper_exchange, owner=profile, id=api_key_id)
        except ApiKey.DoesNotExist:
            raise ApiKeyNotSetException
        with get_redis_connection() as redis_conn:
            key = f"profile_id:{profile.id}-api_key_id:{api_key.id}-exchange:{api_key.exchange}-trade_type:{trade_type}-coin:{coin}"
            user_balance = redis_conn.get(key)
            if not user_balance:
                exchange_client = generate_exchange_client(
                    exchange=exchange,
                    credentials=dict(
                        api_key=api_key.api_key,
                        secret=api_key.secret_key,
                        password=api_key.password,
                    ),
                    sandbox_mode=settings.CCXT_SANDBOX_MODE
                )
                user_balance = exchange_client.get_balance(coin, trade_type)
                redis_conn.set(
                    key,user_balance, 60)
        return Response(
            {
                'api_key_id': api_key.id,
                'balance': user_balance,
                'coin': coin
            },
            status=HTTP_200_OK
        )
