import math
from datetime import datetime, date
from unittest import mock

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from core.choice_field_types import (
    ServiceTypeChoices,
    TradingSignalType,
    PositionChoice,
    StatusChoice
)
from core.test_utils import force_authenticator
from media.models import Media
from services.models import (
    Service,
    DailyAggregatedPnl,
)
from services.tasks import (
    calculate_daily_aggregated_pnl_for_all_dates,
    calculate_today_daily_aggregated_pnl,
    calculate_pnl,
    calculate_roi_and_draw_down,
)
from signals.models import ExchangeMarket, TradingSignal
from user.models import Profile


def mock_today():
    return date(2023, 2, 1)


class SignalServiceDashboardUnitTest(APITestCase):
    def setUp(self) -> None:
        profile = Profile.objects.create(
            owner_id=1000,
            title='test_show_service',
            username='test_show_service',
            is_vendor=True,
        )
        service = Service.objects.create(
            title="dashboard_test",
            description="dashboard_test",
            service_type=ServiceTypeChoices.SIGNAL,
            profile=profile,
            subscription_fee=1000,
            subscription_coin='USDT'
        )
        service.created_at = datetime(2023, 1, 1)
        service.save()
        exchange_market = ExchangeMarket.objects.create(
            exchange_name="exwino",
            coin_pair='USDT/BTC',
            coin_name='BTC-USDT',
            base_currency='BTC',
            quote_currency='USDT',
        )
        media = Media.objects.create(
            key="test_key",
            bucket="test_bucket"
        )
        s1 = TradingSignal.objects.create(
            sid=service,
            type=TradingSignalType.FUTURES,
            position=PositionChoice.LONG,
            exchange_market=exchange_market,
            leverage=5,
            entry_point=1900000,
            entry_point_hit_datetime=datetime.now(),
            percentage_of_fund=10,
            take_profit_1=1950000,
            take_profit_1_hit_datetime=datetime.now(),
            take_profit_2=2000000,
            take_profit_2_hit_datetime=datetime.now(),
            volume=30,
            state=StatusChoice.CLOSE,
            stop_los=1850000,
            description="",
            image_id=media.id,
            virtual_value=100
        )

        s2 = TradingSignal.objects.create(
            sid=service,
            type=TradingSignalType.FUTURES,
            position=PositionChoice.SHORT,
            exchange_market=exchange_market,
            leverage=10,
            entry_point=2000000,
            entry_point_hit_datetime=datetime.now(),
            percentage_of_fund=10,
            take_profit_1=1950000,
            take_profit_1_hit_datetime=datetime.now(),
            take_profit_2=1900000,
            take_profit_2_hit_datetime=datetime.now(),
            volume=30,
            state=StatusChoice.CLOSE,
            stop_los=2150000,
            description="",
            image_id=media.id,
            virtual_value=100
        )

        s3 = TradingSignal.objects.create(
            sid=service,
            type=TradingSignalType.FUTURES,
            position=PositionChoice.SHORT,
            exchange_market=exchange_market,
            leverage=10,
            entry_point=2100000,
            entry_point_hit_datetime=datetime.now(),
            percentage_of_fund=20,
            take_profit_1=2000000,
            take_profit_2=1900000,
            volume=30,
            state=StatusChoice.CLOSE,
            stop_los=2150000,
            stop_los_hit_datetime=datetime.now(),
            description="",
            image_id=media.id,
            virtual_value=100
        )

        s4 = TradingSignal.objects.create(
            sid=service,
            type=TradingSignalType.FUTURES,
            position=PositionChoice.SHORT,
            exchange_market=exchange_market,
            leverage=5,
            entry_point=2200000,
            entry_point_hit_datetime=datetime.now(),
            percentage_of_fund=20,
            take_profit_1=2000000,
            take_profit_2=1900000,
            volume=30,
            stop_los=2350000,
            manual_closure_price=21500,
            state=StatusChoice.CLOSE,
            description="",
            image_id=media.id,
            virtual_value=100
        )

        s5 = TradingSignal.objects.create(
            sid=service,
            type=TradingSignalType.FUTURES,
            position=PositionChoice.LONG,
            exchange_market=exchange_market,
            leverage=10,
            entry_point=2300000,
            entry_point_hit_datetime=datetime.now(),
            percentage_of_fund=20,
            take_profit_1=2400000,
            take_profit_1_hit_datetime=datetime.now(),
            state=StatusChoice.CLOSE,
            stop_los=2250000,
            description="",
            image_id=media.id,
            virtual_value=100
        )

        s1.created_at = datetime(2023, 1, 4)
        s1.closed_datetime = datetime(2023, 1, 4)

        s2.created_at = datetime(2023, 1, 5)
        s2.closed_datetime = datetime(2023, 1, 5)

        s3.created_at = datetime(2023, 1, 8)
        s3.closed_datetime = datetime(2023, 1, 8)

        s4.created_at = datetime(2023, 1, 10)
        s4.closed_datetime = datetime(2023, 1, 10)

        s5.created_at = datetime(2023, 2, 1)
        s5.closed_datetime = datetime(2023, 2, 1)

        s1.save()
        s2.save()
        s3.save()
        s4.save()
        s5.save()


class SignalPnlUnitTest(SignalServiceDashboardUnitTest):

    @mock.patch("services.tasks.date")
    def test_pnl_percentage(self, mock_date):
        mock_date.today = mock_today
        calculate_pnl()
        s1 = TradingSignal.objects.get(created_at=datetime(2023, 1, 4))
        s2 = TradingSignal.objects.get(created_at=datetime(2023, 1, 5))
        s3 = TradingSignal.objects.get(created_at=datetime(2023, 1, 8))
        s4 = TradingSignal.objects.get(created_at=datetime(2023, 1, 10))
        s5 = TradingSignal.objects.get(created_at=datetime(2023, 2, 1))
        self.assertEqual(math.floor(s1.pnl_percentage * 100) / 100.0, 22.36)
        self.assertEqual(math.floor(s2.pnl_percentage * 100) / 100.0, 42.5)
        self.assertEqual(round(s3.pnl_percentage,3), -23.81)
        self.assertEqual(math.floor(s4.pnl_percentage * 100) / 100.0, 11.36)
        self.assertEqual(math.floor(s5.pnl_percentage * 100) / 100.0, 43.47)


class SignalDailyAggregatedPnlUnitTest(SignalServiceDashboardUnitTest):
    @mock.patch("services.tasks.date")
    def test_today_aggregated_pnl(self, mock_date):
        mock_date.today = mock_today
        calculate_pnl()
        calculate_today_daily_aggregated_pnl()
        today_aggregated_pnl = DailyAggregatedPnl.objects.get(
            date=mock_date.today()
        )
        self.assertEqual(
            math.floor(
                today_aggregated_pnl.percentage * 100
            ) / 100.0, 8.69
        )

    @mock.patch("services.tasks.date")
    def test_aggregated_pnl(self, mock_date):
        mock_date.today = mock_today
        calculate_pnl()
        calculate_daily_aggregated_pnl_for_all_dates()
        pnl_1 = DailyAggregatedPnl.objects.get(date=date(2023, 1, 4))
        pnl_2 = DailyAggregatedPnl.objects.get(date=date(2023, 1, 5))
        pnl_3 = DailyAggregatedPnl.objects.get(date=date(2023, 1, 8))
        pnl_4 = DailyAggregatedPnl.objects.get(date=date(2023, 1, 10))
        pnl_5 = DailyAggregatedPnl.objects.get(date=date(2023, 2, 1))
        self.assertEqual(math.floor(pnl_1.percentage * 100) / 100.0, 2.23)
        self.assertEqual(math.floor(pnl_2.percentage * 100) / 100.0, 4.25)
        self.assertEqual(math.floor(pnl_3.percentage * 100) / 100.0, -4.77)
        self.assertEqual(math.floor(pnl_4.percentage * 100) / 100.0, 2.27)
        self.assertEqual(math.floor(pnl_5.percentage * 100) / 100.0,8.69)


class SignalROIUnitTest(SignalServiceDashboardUnitTest):

    @mock.patch("services.tasks.date")
    @mock.patch("services.api.views.dashboard.date")
    @mock.patch("services.cache_utils.date")
    @force_authenticator
    def test_today_aggregated_pnl(self, mock_date, mock_dashboard_date, mock_cache_utils_date):
        mock_date.today = mock_today
        mock_dashboard_date.today = mock_today
        mock_cache_utils_date.today = mock_today
        calculate_pnl()
        calculate_today_daily_aggregated_pnl()
        calculate_roi_and_draw_down()
        service = Service.objects.get(
            title="dashboard_test",
            description="dashboard_test",
        )
        url = reverse(
            'service_dashboard-cumulative-roi',
            kwargs=dict(pk=service.pk)
        ) + "?history_type=monthly"
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        roi_list = response.json()
        self.assertIsInstance(roi_list, list)
        self.assertEqual(len(roi_list), 30)
        self.assertEqual(
            math.floor(
                roi_list[0]["percentage"] * 100
            ) / 100.0, 0
        )
        self.assertEqual(
            math.floor(
                roi_list[1]["percentage"] * 100
            ) / 100.0, 2.23
        )
        for i in range(2, 5):
            self.assertEqual(
                math.floor(
                    roi_list[i]["percentage"] * 100
                ) / 100.0, 6.48
            )
        for i in range(5, 7):
            self.assertEqual(
                math.floor(
                    roi_list[i]["percentage"] * 100
                ) / 100.0, 1.72
            )
        for i in range(7, 29):
            self.assertEqual(
                math.floor(
                    roi_list[i]["percentage"] * 100
                ) / 100.0, 3.99
            )
        self.assertEqual(
            math.floor(
                roi_list[29]["percentage"] * 100
            ) / 100.0, 12.69
        )


