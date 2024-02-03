from unittest import mock

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from core.choice_field_types import TradingSignalType, PositionChoice, StatusChoice
from core.test_utils import force_authenticator
from core.utils import convertor
from media.models import Media
from services.models import Service
from signals.models import TradingSignal, ExchangeMarket
from user.models import Profile


class UpdateSignalUnitTest(APITestCase):
    def setUp(self):
        profile = Profile.objects.create(
            owner_id=1,
            title='test_profile',
            username='test_profile',
            is_vendor=True,
        )

        service = Service.objects.create(
            title='signal',
            link='http://exwino/test/service',
            description='for testing',
            profile=profile,
            coin='USDT',
            subscription_fee=100,
        )
        Media.objects.create(
            key="test_key",
            bucket="test_bucket"
        )
        exchange_market = ExchangeMarket.objects.create(
            exchange_name='exwino',
            coin_pair='BTCUSDT',
            coin_name='USDT/BTC',
            base_currency='BTC',
            quote_currency='USDT',
        )
        TradingSignal.objects.create(
            sid=Service.objects.get(link='http://exwino/test/service'),
            type=TradingSignalType.SPOT,
            exchange_market=exchange_market,
            leverage=1000000,
            entry_point=50,
            percentage_of_fund=0.1,
            take_profit_1=200,
            stop_los=300,
            description="for test the update signal",
            image_id=Media.objects.get(key='test_key').id,
            virtual_value=100
        )
        TradingSignal.objects.create(
            sid=Service.objects.get(link='http://exwino/test/service'),
            state=StatusChoice.START,
            type=TradingSignalType.FUTURES,
            position=PositionChoice.LONG,
            exchange_market=exchange_market,
            leverage=1,
            volume=10,
            entry_point=25876.8,
            take_profit_1=25880,
            take_profit_2=25888,
            stop_los=25860,
            percentage_of_fund=10,
            description="test stop los price update.",
            image_id=Media.objects.get(key='test_key').id,
            pnl_percentage=0.10,
            pnl_amount=10,
            virtual_value=100
        )
        TradingSignal.objects.create(
            sid=Service.objects.get(link='http://exwino/test/service'),
            state=StatusChoice.START,
            type=TradingSignalType.FUTURES,
            position=PositionChoice.SHORT,
            exchange_market=exchange_market,
            leverage=1,
            volume=10,
            percentage_of_fund=10,
            entry_point=5876.8,
            take_profit_1=25860,
            take_profit_2=25870,
            stop_los=25890,
            description="test stop los price update.",
            image_id=Media.objects.get(key='test_key').id,
            pnl_percentage=0.10,
            pnl_amount=10,
            virtual_value=100
        )

    @force_authenticator
    @mock.patch("core.api_gateways.ProducerClientGateway.produce", return_value=True)
    def test_update_signal(self, mocked):
        trading = TradingSignal.objects.get(description="for test the update signal")
        url = reverse('signal-detail', kwargs={'pk': trading.id})
        response = self.client.patch(url, data={'description': "is done"}, format='json')
        trading.refresh_from_db()
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
        self.assertEqual(
            trading.description,
            "for test the update signal" + '=====' + "is done"
        )

    @force_authenticator
    @mock.patch("core.api_gateways.ProducerClientGateway.produce", return_value=True)
    def test_update_long_signal_sl_price_risk_free(self, mocked):
        trading = TradingSignal.objects.get(position=PositionChoice.LONG)
        data = {
            "entry_point": 25876.8,
            "take_profit_1": 25890,
            "take_profit_2": 25900,
            "stop_los": 25800,
            "exchange_market": ExchangeMarket.objects.first().id,
            "leverage": 1,
            "image_id": Media.objects.first().id,
            "percentage_of_fund": 10,
            "position": "LONG",
            "type": "FUTURES",
            "volume": 10,
            "vip": False
        }
        url = reverse('signal-detail', kwargs={'pk': trading.id})
        response = self.client.put(url, data=data, format='json')
        trading.refresh_from_db()
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

    @force_authenticator
    @mock.patch("core.api_gateways.ProducerClientGateway.produce", return_value=True)
    def test_update_long_signal_sl_price_bigger_than_tp_risk_free(self, mocked):
        trading = TradingSignal.objects.get(position=PositionChoice.LONG)
        data = {
            "entry_point": 25876.8,
            "take_profit_1": 25890,
            "take_profit_2": 25900,
            "stop_los": 25900,
            "exchange_market": ExchangeMarket.objects.first().id,
            "leverage": 1,
            "image_id": Media.objects.first().id,
            "percentage_of_fund": 10,
            "position": "LONG",
            "type": "FUTURES",
            "volume": 10,
            "vip": False
        }
        url = reverse('signal-detail', kwargs={'pk': trading.id})
        response = self.client.put(url, data=data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    @force_authenticator
    @mock.patch("core.api_gateways.ProducerClientGateway.produce", return_value=True)
    def test_update_short_signal_sl_price_risk_free(self, mocked):
        trading = TradingSignal.objects.get(position=PositionChoice.SHORT)
        data = {
            "entry_point": 25876.8,
            "take_profit_1": 25860,
            "take_profit_2": 25850,
            "stop_los": 25870,
            "exchange_market": ExchangeMarket.objects.first().id,
            "leverage": 1,
            "image_id": Media.objects.first().id,
            "percentage_of_fund": 10,
            "position": "SHORT",
            "type": "FUTURES",
            "volume": 10,
            "vip": False
        }
        url = reverse('signal-detail', kwargs={'pk': trading.id})
        response = self.client.put(url, data=data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

    @force_authenticator
    @mock.patch("core.api_gateways.ProducerClientGateway.produce", return_value=True)
    def test_update_short_signal_invalid_sl_price_risk_free(self, mocked):
        trading = TradingSignal.objects.get(position=PositionChoice.SHORT)
        data = {
            "entry_point": 25876.8,
            "take_profit_1": 25860,
            "take_profit_2": 25850,
            "stop_los": 25855,
            "exchange_market": ExchangeMarket.objects.first().id,
            "leverage": 1,
            "image_id": Media.objects.first().id,
            "percentage_of_fund": 10,
            "position": "SHORT",
            "type": "FUTURES",
            "volume": 10,
            "vip": False
        }
        url = reverse('signal-detail', kwargs={'pk': trading.id})
        response = self.client.put(url, data=data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    @force_authenticator
    @mock.patch("core.api_gateways.ProducerClientGateway.produce", return_value=True)
    def test_update_long_signal_sl_price_risk_free(self, mocked):
        trading = TradingSignal.objects.get(type=TradingSignalType.SPOT)
        data = {
            "entry_point": 25876.8,
            "take_profit_1": 25890,
            "take_profit_2": 25900,
            "stop_los": 25800,
            "exchange_market": ExchangeMarket.objects.first().id,
            "leverage": 1,
            "image_id": Media.objects.first().id,
            "percentage_of_fund": 10,
            "position": "LONG",
            "type": "FUTURES",
            "volume": 10,
            "vip": False
        }
        url = reverse('signal-detail', kwargs={'pk': trading.id})
        response = self.client.put(url, data=data, format='json')
        trading.refresh_from_db()
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

    @force_authenticator
    @mock.patch("core.api_gateways.ProducerClientGateway.produce", return_value=True)
    def test_update_long_signal_sl_price_bigger_than_tp_risk_free(self, mocked):
        trading = TradingSignal.objects.get(type=TradingSignalType.SPOT)
        data = {
            "entry_point": 25876.8,
            "take_profit_1": 25890,
            "take_profit_2": 25900,
            "stop_los": 25900,
            "exchange_market": ExchangeMarket.objects.first().id,
            "leverage": 1,
            "image_id": Media.objects.first().id,
            "percentage_of_fund": 10,
            "position": "LONG",
            "type": "FUTURES",
            "volume": 10,
            "vip": False
        }
        url = reverse('signal-detail', kwargs={'pk': trading.id})
        response = self.client.put(url, data=data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )
