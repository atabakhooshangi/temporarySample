import datetime
import json
import logging
import traceback
from datetime import date, timedelta
from datetime import datetime
from typing import Tuple, List

import pytz
import requests
from django.conf import settings
from django.db.models import Sum, QuerySet, FloatField, Q, F, DateField, Count, Case, When, Value
from django.db.models.functions import Coalesce, Cast
from django_redis import get_redis_connection

from copytrading.models import Position
from core.celery import app
from core.choice_field_types import (
    StatusChoice,
    HistoryTypeChoices,
    ServiceTypeChoices,
    PositionStatusChoices
)
from core.date_utils import days_between_dates
from core.email_utils import send_email
from services.cache_utils import cache_roi_and_draw_down
from services.models import (
    DailyROI,
    ROIHistory,
    Service,
    DailyAggregatedPnl,
)
from signals.models import TradingSignal, SignalVirtualBalance
from signals.pnl import SignalPnLCalculator
from user.models import User

logger = logging.getLogger(__name__)


def calculate_signals_pnl(
        signals: QuerySet[TradingSignal]
) -> Tuple[List, List]:
    successful_calculations = []
    failed_calculations = []
    signal: TradingSignal
    for signal in signals:
        try:
            calculation_result = SignalPnLCalculator(
                signal,
                quote_currency=signal.exchange_market.quote_currency,
                base_currency=signal.exchange_market.base_currency,
            ).pnl_calculator()
            signal.pnl_amount = calculation_result["pnl_amount"]
            signal.pnl_percentage = calculation_result["pnl_percentage"]
            successful_calculations.append(dict(
                signal_id=signal.id,
                pnl_amount=calculation_result["pnl_amount"],
                pnl_percentage=calculation_result["pnl_percentage"],
            ))
        except Exception as _:  # noqa
            failed_calculations.append(dict(
                signal_id=signal.id,
                exception_detail=traceback.format_exc()
            ))
    TradingSignal.objects.bulk_update(signals, fields=["pnl_amount", "pnl_percentage"])
    return successful_calculations, failed_calculations


@app.task(name="calculate_pnl")
def calculate_pnl(services_id_list: List = None):
    """
    Calculate pnl for closed signals
    """
    state_filter = Q(state=StatusChoice.CLOSE)
    if services_id_list:
        state_filter &= Q(sid_id__in=services_id_list)
    signals = TradingSignal.objects.filter(state_filter)
    successful_calculations, failed_calculations = calculate_signals_pnl(signals)
    return dict(
        successful_calculations=successful_calculations,

        failed_calculations=failed_calculations
    )


@app.task(name="calculate_today_daily_aggregated_pnl")
def calculate_today_daily_aggregated_pnl(services_id_list: List = None):
    """
    Calculate aggregated pnl for today closed signals
    """
    services = Service.objects.all()
    if services_id_list:
        services = services.filter(id__in=services_id_list)
    service: Service
    for service in services:
        if service.service_type == ServiceTypeChoices.SIGNAL:
            virtual_balance = SignalVirtualBalance.objects.filter(service=service).last()
            if virtual_balance:
                yesterday_pnl = DailyAggregatedPnl.objects.filter(service=service, date__lt=date.today()).order_by('-date').first()
                today_balance = virtual_balance.balance
                change = round(((virtual_balance.balance - yesterday_pnl.v_balance) / yesterday_pnl.v_balance) * 100, 2) if yesterday_pnl is not None else 0
            else:
                change = 0
                today_balance = 0
            aggregated_pnl = TradingSignal.objects.filter(
                closed_datetime__date=date.today(),
                state=StatusChoice.CLOSE,
                sid=service,
            ).annotate(
                date_profit_percentage_sum_with_pof=F('pnl_percentage') * F('percentage_of_fund') / 100, ).aggregate(
                percentage=Coalesce(Sum("date_profit_percentage_sum_with_pof"), 0.0, output_field=FloatField()),
                amount=Coalesce(Sum("pnl_amount"), 0.0, output_field=FloatField())
            )
        elif service.service_type == ServiceTypeChoices.COPY:
            change = 0
            today_balance = 0
            aggregated_pnl = Position.objects.filter(
                closed_datetime__date=date.today(),
                status=PositionStatusChoices.CLOSED,
                trading_order__service=service,
            ).distinct().aggregate(
                percentage=Coalesce(
                    Sum("closed_pnl_percentage"), 0.0, output_field=FloatField()
                ),
                amount=Coalesce(
                    Sum("closed_pnl"), 0.0, output_field=FloatField()
                )
            )
        DailyAggregatedPnl.objects.update_or_create(
            date=date.today(),
            service=service,
            defaults=dict(
                percentage=aggregated_pnl["percentage"],
                amount=aggregated_pnl["amount"],
                v_balance=today_balance,
                v_balance_change=change,
            )
        )


@app.task(name="calculate_daily_aggregated_pnl_for_all_dates")
def calculate_daily_aggregated_pnl_for_all_dates(services_id_list: List = None):
    """
    Calculate aggregated pnl for all signals till now from platform begining date
    """
    services = Service.objects.all()
    if services_id_list:
        services = services.filter(id__in=services_id_list)
    all_dates = days_between_dates(
        settings.PLATFORM_BEGINING_DATE,
        date.today()
    )
    service: Service
    for service in services:
        if service.service_type == ServiceTypeChoices.SIGNAL:
            items = TradingSignal.objects.filter(sid=service, ).annotate(
                profit_percentage_with_pof=F('pnl_percentage') * F('percentage_of_fund') / 100.0
            )

            items = items.values(
                closed_datetime__date=Cast('closed_datetime', DateField())
            ).annotate(
                date_profit_percentage_sum=Sum('profit_percentage_with_pof'),
                date_profit_amount_sum=Sum('pnl_amount')
            ).order_by('closed_datetime__date')



        elif service.service_type == ServiceTypeChoices.COPY:
            items = Position.objects.filter(
                trading_order__service=service,
            ).distinct() \
                .values("closed_datetime__date") \
                .annotate(
                date_profit_percentage_sum=Coalesce(Sum("closed_pnl_percentage"), 0.0, output_field=FloatField()),
                date_profit_amount_sum=Coalesce(Sum("closed_pnl"), 0.0, output_field=FloatField())
            ) \
                .order_by("closed_datetime__date")
        for date_obj in all_dates:
            aggregated_pnl = next(
                (
                    item for item in items
                    if str(item["closed_datetime__date"]) == str(date_obj)
                ),
                dict(date_profit_percentage_sum=0, date_profit_amount_sum=0)
            )
            DailyAggregatedPnl.objects.update_or_create(
                date=date_obj,
                service=service,
                defaults=dict(
                    percentage=aggregated_pnl["date_profit_percentage_sum"],
                    amount=aggregated_pnl["date_profit_amount_sum"],
                )
            )


def calculate_roi_history(
        service: Service,
        history_type: HistoryTypeChoices.names,
):
    """
    Calculates and update the ROI of the selected service
    for the chosen history_type(weekly, monthly, three_monthly and 
    from the service creation time)
    """
    today = date.today()
    roi_history, _ = ROIHistory.objects.get_or_create(
        service=service,
        history_type=history_type,
    )
    if history_type == HistoryTypeChoices.WEEKLY:
        start = today - timedelta(days=6)
    elif history_type == HistoryTypeChoices.TWO_WEEKLY:
        start = today - timedelta(days=13)
    elif history_type == HistoryTypeChoices.MONTHLY:
        start = today - timedelta(days=29)
    elif history_type == HistoryTypeChoices.TWO_MONTHLY:
        start = today - timedelta(days=59)
    elif history_type == HistoryTypeChoices.THREE_MONTHLY:
        start = today - timedelta(days=89)
    elif history_type == HistoryTypeChoices.OVERALLY:
        start = service.created_at.date() - timedelta(days=1)
    else:
        return
    dates = days_between_dates(start_date=start, end_date=today)
    if not dates:
        return
    # remove today because we dont want to include today pnl
    # in the roi
    dates.pop()
    if service.service_type == ServiceTypeChoices.SIGNAL:
        items = TradingSignal.objects.filter(
            closed_datetime__date__range=[dates[0], dates[-1]],
            sid=service,
        ).annotate(
            profit_percentage_with_pof=F('pnl_percentage') * F('percentage_of_fund') / 100.0
        )
        items = items.values(
            closed_datetime__date=Cast('closed_datetime', DateField())
        ).annotate(
            date_profit_sum=Sum('profit_percentage_with_pof'),
            date_profit_amount_sum=Coalesce(
                Sum("pnl_amount"), 0.0, output_field=FloatField()
            )
        ).order_by('closed_datetime__date')

    elif service.service_type == ServiceTypeChoices.COPY:
        items = Position.objects.filter(
            closed_datetime__date__range=[dates[0], dates[-1]],
            trading_order__service=service,
        ) \
            .values("closed_datetime__date") \
            .annotate(
            date_profit_sum=Coalesce(
                Sum("closed_pnl_percentage"), 0.0, output_field=FloatField()
            ),
            date_profit_amount_sum=Coalesce(
                Sum("closed_pnl"), 0.0, output_field=FloatField()
            )
        ) \
            .order_by("closed_datetime__date")

    profit = items[0]['date_profit_sum'] if (len(items) != 0 and items[0]['closed_datetime__date'] == dates[0]) else 0
    profit_amount = items[0]['date_profit_amount_sum'] if (len(items) != 0 and items[0]['closed_datetime__date'] == dates[0]) else 0
    roi_number = 1
    DailyROI.objects.update_or_create(
        number=roi_number,
        roi_history=roi_history,
        defaults=dict(
            date=dates[0],
            percentage=items[0]['date_profit_sum'] if (len(items) != 0 and items[0]['closed_datetime__date'] == dates[0]) else 0,
            amount=items[0]['date_profit_amount_sum'] if (len(items) != 0 and items[0]['closed_datetime__date'] == dates[0]) else 0,
        )
    )
    for date_obj in dates[1:]:
        date_profit = next(
            (
                item for item in items
                if str(item["closed_datetime__date"]) == str(date_obj)
            ),
            dict(date_profit_sum=0,date_profit_amount_sum=0)
        )
        profit += date_profit["date_profit_sum"]
        profit_amount += date_profit["date_profit_amount_sum"]
        roi_number += 1
        DailyROI.objects.update_or_create(
            roi_history=roi_history,
            number=roi_number,
            defaults=dict(percentage=profit, date=date_obj,amount=profit_amount ),
        )
    return


@app.task(name="calculate_roi_and_draw_down")
def calculate_roi_and_draw_down(services_id_list: List = None):
    """
    Calculate the ROI(return of investment) and the draw down
    for all the service and for all available history type
    """
    services = Service.objects.all()
    if services_id_list:
        services = services.filter(id__in=services_id_list)
    for service in services:
        draw_down_data = {}
        initial_draw_down_data = {}
        for history_type in HistoryTypeChoices.names:
            calculate_roi_history(service, history_type)
            data = cache_roi_and_draw_down(service=service,
                                           expire_in=24 * 60 * 60,
                                           history_type=history_type,
                                           include_current_day=True
                                           )
            draw_down_data[history_type] = data["draw_down"]
            initial_draw_down_data[history_type] = data["initial_draw_down"]
        service.draw_down = draw_down_data
        service.initial_draw_down = initial_draw_down_data
    Service.objects.bulk_update(
        services,
        fields=["draw_down", "initial_draw_down"]
    )


@app.task(name="pending_service_send_email")
def pending_service_send_email(username: str):
    """
    Send email to admin when a vendor submit a public service request
    """
    recipient = list(User.objects.filter(is_active=True, groups__name='support').values_list(
        "email",
        flat=True
    ))
    send_email(
        subject="ثبت درخواست وندر شدن",
        message=f"کاربر {username} برای تریدر شدن درخواست داده است لطفا بررسی بفرمایید",
        recipient_list=recipient
        ,
    )
    logger.info(f'For vendor request email sand to {recipient} at {datetime.now()}')


@app.task(name="fetch_console_setting", queue='celery')
def get_console_setting():
    try:
        resp = requests.get(f"{settings.CONFIG_SERVER_BASE_URL}{settings.CONSOLE_KEY}?raw=true").json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching console setting: {e}")
        return None
    with get_redis_connection("data_cache") as redis_conn:
        redis_conn.set(
            settings.CONSOLE_SETTINGS_REDIS_KEY,
            json.dumps(resp),
        )


@app.task(name="frozen_balance_correction")
def frozen_balance_correction(service_list: list):
    deploy_exact_time = pytz.timezone("UTC").localize(datetime(2024, 1, 6, 12, 0, 0))
    services_with_open_signals = Service.objects.annotate(
        published_start_signals_count=Count(Case(
            When(
                service_signal__state__in=['PUBLISH', 'START'],
                service_signal__created_at__gt=deploy_exact_time,
                then=1)
        )),
        total_virtual_value=Coalesce(Sum(Case(
            When(
                service_signal__state__in=['PUBLISH', 'START'],
                service_signal__child_id__isnull=True,
                service_signal__created_at__gt=deploy_exact_time,
                then='service_signal__virtual_value'),
            default=Value(0.0)
        )), 0.0, output_field=FloatField())
    ).select_related(
        'virtual_value'
    ).filter(
        published_start_signals_count__gt=0,
        id__in=service_list
    )

    for service in services_with_open_signals:
        service.virtual_value.frozen = service.total_virtual_value
        service.virtual_value.save()


@app.task(name="total_balance_correction")
def total_balance_correction(service_list: list):
    deploy_exact_time = pytz.timezone("UTC").localize(datetime(2024, 1, 6, 12, 0, 0))
    services_with_open_signals = Service.objects.annotate(
        signals_after_publish=Count(Case(
            When(service_signal__created_at__gt=deploy_exact_time,
                 then=1)
        )),
        total_pnl_amount=Coalesce(Sum(Case(
            When(service_signal__state__in=['CLOSE'],
                 service_signal__child_id__isnull=True,
                 service_signal__created_at__gt=deploy_exact_time,
                 then='service_signal__pnl_amount'),
            default=Value(0.0)
        )), 0.0, output_field=FloatField())
    ).select_related(
        'virtual_value'
    ).filter(
        signals_after_publish__gt=0,
        id__in=service_list
    )
    for service in services_with_open_signals:
        try:
            service_list.remove(str(service.id))
        except Exception:
            continue
        service.virtual_value.balance = 1000 + service.total_pnl_amount
        service.virtual_value.save()

    # correction of services with no signals after publish
    services_with_no_signals_after_publish = Service.objects.select_related(
                                                                            'virtual_value'
                                                                        ).filter(
                                                                            id__in=service_list
                                                                        )
    for service in services_with_no_signals_after_publish:
        service.virtual_value.balance = 1000
        service.virtual_value.save()