from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from core.choice_field_types import TradingSignalType, PositionChoice
from core.message_text import MessageText
from core.test_utils import force_authenticator
from media.models.media import Media
from services.models import Service
from signals.models import ExchangeMarket
from user.models.profile import Profile
from django.utils.translation import gettext_lazy as _


class TradingSignalUnitTest(APITestCase):

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
        ExchangeMarket.objects.create(
            exchange_name='exwino',
            coin_pair='BTCUSDT',
            coin_name='USDT/BTC',
            base_currency='BTC',
            quote_currency='USDT',
        )
        Media.objects.create(
            key="test_key",
            bucket="test_bucket"
        )

    def test_unauthorized_user(self):
        url = reverse('signal-list')
        response = self.client.post(url, data={}, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    @force_authenticator
    def test_create_spot_signal(self):
        url = reverse('signal-list')
        data = {
            "type": TradingSignalType.SPOT,
            "exchange_market": ExchangeMarket.objects.get(exchange_name="exwino").id,
            "leverage": 1,
            "entry_point": 100,
            "percentage_of_fund": 3,
            "take_profit_1": 200,
            "stop_los": 50,
            "description": "first creations",
            "image_id": Media.objects.get(key='test_key').id,
            "virtual_value":100
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

    @force_authenticator
    def test_create_spot_signal_without_tp_1(self):
        url = reverse('signal-list')
        data = {

            "type": TradingSignalType.SPOT,
            "exchange_market": ExchangeMarket.objects.get(exchange_name="exwino").id,
            "leverage": 3,
            "entry_point": 50,
            "percentage_of_fund": 1,
            "stop_los": 300,
            "description": "first creations",
            "image_id": Media.objects.get(key='test_key').id,
            "virtual_value": 100
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    @force_authenticator
    def test_create_futures_signal(self):
        url = reverse('signal-list')
        data = {

            "type": TradingSignalType.FUTURES,
            "exchange_market": ExchangeMarket.objects.get(exchange_name="exwino").id,
            "leverage": 1,
            "entry_point": 50,
            "percentage_of_fund": 25,
            "take_profit_1": 40,
            "position": PositionChoice.SHORT,
            "stop_los": 60,
            "description": "first creations",
            "image_id": Media.objects.get(key='test_key').id,
            "virtual_value":100
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

    @force_authenticator
    def test_create_futures_signal_Long_position_stop_los_bigger_than_entry_point(self):
        url = reverse('signal-list')
        data = {

            "type": TradingSignalType.FUTURES,
            "exchange_market": ExchangeMarket.objects.get(exchange_name="exwino").id,
            "percentage_of_fund": 1,
            "position": PositionChoice.LONG,
            "entry_point": 1000000,
            "take_profit_1": 1200000,
            "stop_los": 1100000,
            "description": "first creations",
            "image_id": Media.objects.get(key='test_key').id,
            "virtual_value": 100
        }
        response = self.client.post(url, data, format='json')
        data = dict(response.data)
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )
        self.assertIn(
            'stop_los',
            list(data.keys()),
        )

        self.assertIn(
            MessageText.StopLosValueNotAcceptable406,
            data['stop_los']
        )

    @force_authenticator
    def test_create_futures_signal_short_position_stop_los_less_than_entry_point(self):
        url = reverse('signal-list')
        data = {
            "type": TradingSignalType.FUTURES,
            "exchange_market": ExchangeMarket.objects.get(exchange_name="exwino").id,
            "percentage_of_fund": 1,
            "position": PositionChoice.SHORT,
            "entry_point": 1000000,
            "take_profit_1": 100000,
            "stop_los": 200000,
            "description": "first creations",
            "image_id": Media.objects.get(key='test_key').id,
            "virtual_value": 100
        }
        response = self.client.post(url, data, format='json')
        data = dict(response.data)
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )
        self.assertIn(
            'stop_los',
            list(data.keys())
        )

        self.assertIn(
            MessageText.StopLosValueNotAcceptable406,
            data['stop_los']
        )

    @force_authenticator
    def test_create_futures_signal_Long_position_take_profit_1_less_than_entry_point(self):
        url = reverse('signal-list')
        data = {
            "type": TradingSignalType.FUTURES,
            "exchange_market": ExchangeMarket.objects.get(exchange_name="exwino").id,
            "percentage_of_fund": 1,
            "position": PositionChoice.LONG,
            "entry_point": 1000000,
            "take_profit_1": 200000,
            "stop_los": 900000,
            "description": "first creations",
            "image_id": Media.objects.get(key='test_key').id,
            "virtual_value": 100
        }
        response = self.client.post(url, data, format='json')
        data = dict(response.data)
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )
        self.assertIn(
            'take_profit_1',
            list(data.keys()))

        self.assertIn(
            MessageText.TakeProfit1ValueNotAcceptable406,
            data['take_profit_1'],
        )

    @force_authenticator
    def test_create_futures_signal_short_position_take_profit_1_bigger_than_entry_point(self):
        url = reverse('signal-list')
        data = {
            "type": TradingSignalType.FUTURES,
            "exchange_market": ExchangeMarket.objects.get(exchange_name="exwino").id,
            "percentage_of_fund": 1,
            "position": PositionChoice.SHORT,
            "entry_point": 1000000,
            "take_profit_1": 2000000,
            "stop_los": 9000000,
            "description": "first creations",
            "image_id": Media.objects.get(key='test_key').id,
            "virtual_value": 100
        }
        response = self.client.post(url, data, format='json')
        data = dict(response.data)
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )
        self.assertIn(
            'take_profit_1',
            list(data.keys())[0],
        )

        self.assertIn(
            MessageText.TakeProfit1ValueNotAcceptable406,
            data['take_profit_1'],
        )

    @force_authenticator
    def test_create_futures_signal_Long_position_take_profit_1_less_than_entry_point(self):
        url = reverse('signal-list')
        data = {
            "type": TradingSignalType.FUTURES,
            "exchange_market": ExchangeMarket.objects.get(exchange_name="exwino").id,
            "percentage_of_fund": 1,
            "position": PositionChoice.LONG,
            "entry_point": 1000000,
            "take_profit_1": 200000,
            "stop_los": 900000,
            "description": "first creations",
            "image_id": Media.objects.get(key='test_key').id,
            "virtual_value": 100
        }
        response = self.client.post(url, data, format='json')
        data = dict(response.data)
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )
        self.assertIn(
            'take_profit_1',
            list(data.keys())
        )

        self.assertIn(
            MessageText.TakeProfit1ValueNotAcceptable406,
            data['take_profit_1']

        )

    @force_authenticator
    def test_create_signal_with_tp_2_without_volume(self):
        url = reverse('signal-list')
        data = {
            "type": TradingSignalType.SPOT,
            "exchange_market_id": ExchangeMarket.objects.get(exchange_name="exwino").id,
            "leverage": 1000000,
            "entry_point": 23000,
            "percentage_of_fund": 5,
            "take_profit_1": 22600,
            "take_profit_2": 22800,
            "stop_los": 23300,
            "description": "first creations",
            "image_id": Media.objects.get(key='test_key').id,
            "virtual_value": 100
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    @force_authenticator
    def test_create_signal_with_tp_2_with_volume(self):
        url = reverse('signal-list')
        data = {
            "type": TradingSignalType.SPOT,
            "exchange_market": ExchangeMarket.objects.get(exchange_name="exwino").id,
            "leverage": 1000000,
            "entry_point": 100,
            "percentage_of_fund": 1,
            "take_profit_1": 200,
            "take_profit_2": 300,
            "volume": 1,
            "stop_los": 50,
            "description": "first creations",
            "image_id": Media.objects.get(key='test_key').id,
            "virtual_value": 100
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

    @force_authenticator
    def test_unvalid_data_negative_leverage(self):
        url = reverse('signal-list')
        data = {
            "type": TradingSignalType.SPOT,
            "exchange_market": ExchangeMarket.objects.get(exchange_name="exwino").id,
            "leverage": -1000000,
            "entry_point": 50,
            "percentage_of_fund": 1,
            "take_profit_1": 200,
            "take_profit_2": 200,
            "volume": 1,
            "stop_los": 300,
            "description": "first creations",
            "image_id": Media.objects.get(key='test_key').id,
            "virtual_value": 100
        }
        response = self.client.post(url, data, format='json', HTTP_ACCEPT_LANGUAGE='en')
        data = dict(response.data)
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )
        self.assertIn(
            'leverage',
            list(data.keys()),
        )

        self.assertIn(
            _('Ensure this value is greater than or equal to 1.'),
            data['leverage'],

        )

    @force_authenticator
    def test_unvalid_data_for_percentage(self):
        url = reverse('signal-list')
        data = {
            "type": TradingSignalType.SPOT,
            "exchange_market": ExchangeMarket.objects.get(exchange_name="exwino").id,
            "leverage": 10000,
            "entry_point": 50,
            "percentage_of_fund": 120,
            "take_profit_1": 200,
            "take_profit_2": 200,
            "volume": 1,
            "stop_los": 300,
            "description": "first creations",
            "image_id": Media.objects.get(key='test_key').id,
            "virtual_value": 100
        }
        response = self.client.post(url, data, format='json',HTTP_ACCEPT_LANGUAGE='en')

        data = dict(response.data)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )
        self.assertIn(
            'percentage_of_fund',
            list(data.keys())
        )

        self.assertIn(
            "Ensure this value is less than or equal to 30.",
            data['percentage_of_fund']

        )

    @force_authenticator
    def test_create_signal_Long_tp2_less_than_tp1(self):
        url = reverse('signal-list')
        data = {
            "type": TradingSignalType.FUTURES,
            "position": PositionChoice.LONG,
            "exchange_market": ExchangeMarket.objects.get(exchange_name="exwino").id,
            "leverage": 1000000,
            "entry_point": 50,
            "percentage_of_fund": 1,
            "take_profit_1": 200,
            "take_profit_2": 100,
            "volume": 1,
            "stop_los": 400,
            "description": "first creations",
            "image_id": Media.objects.get(key='test_key').id,
            "virtual_value": 100
        }
        response = self.client.post(url, data, format='json',HTTP_ACCEPT_LANGUAGE='en')
        data = dict(response.data)
        self.assertIn(
            'take_profit_2',
            list(data.keys())
        )

        self.assertIn(
            "take profit 2 is less than take profit 1.",
            data['take_profit_2']

        )
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )
