import json
import math
from datetime import timedelta, date, datetime

from django.db import models
from django.db.models import Count, Avg, OuterRef, F
from django.db.models.functions import (
    Cast,
    Coalesce,
    Abs,
    Round,
)
from django.http import Http404, QueryDict
from django_redis import get_redis_connection
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.viewsets import GenericViewSet
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from copytrading.models import Position
from core.choice_field_types import (
    HistoryTypeChoices,
    ServiceTypeChoices,
    StatusChoice,
    PositionStatusChoices
)
from rest_framework.request import Request
from rest_framework.decorators import action
from core.date_utils import previous_week_range, days_between_dates
from core.sql_functions import PostgresExtractMinute, SubqueryCount, RoundWithPlaces
from services.cache_utils import cache_roi_and_draw_down
from services.models import (
    Service,
    DailyAggregatedPnl,
    Subscription
)
from signals.models import TradingSignal, VendorFollower
from signals.pnl import risk_evaluation
from services.serializers.service import ServiceReadOnlySerializer


class SignalServiceDashboardMixin:

    def get_signals_queryset(self, query_params: dict):
        service: Service = self.get_object()
        if service.service_type == ServiceTypeChoices.SIGNAL:
            # IF data at database clean signal with closed datetime is close because that\'s not
            # (signals exist with a state opposite of close but have close datetime)check the state for double check,
            # This problem does not related to code.
            base_queryset = TradingSignal.objects.filter(sid=service,
                                                         state=StatusChoice.CLOSE)
            history_type = query_params.get("history_type")
            if history_type:
                history_type = history_type.upper()
                if history_type not in HistoryTypeChoices.names:
                    raise APIException(
                        "Invalid history type. please select on the following "
                        + ", ".join(HistoryTypeChoices.names)
                    )
                start, end = self.get_history_type_date_range(history_type)
                return base_queryset.filter(
                    closed_datetime__date__range=[start, end]
                )
            return base_queryset

        raise Http404

    def signal_statistics(
            self,
            request,
            *args,
            **kwargs
    ):
        base_queryset = self.get_signals_queryset(request.query_params)
        service: Service = self.get_object()
        weeks_since_service_creation = (
                                               date.today() - service.created_at.date()
                                       ).days // 7 + 1
        result = base_queryset \
            .annotate(
            open_duration=(
                    models.F("closed_datetime") - models.F("start_datetime")
            ),
        ) \
            .aggregate(
            signals_count=models.Count("id"),
            closed_signals_pnl_amount_gt_zero_count=models.Count(
                "id",
                filter=models.Q(
                    pnl_amount__gt=0,
                    state=StatusChoice.CLOSE,
                )
            ),
            closed_signals_count=models.Count(
                "id", filter=models.Q(
                    state=StatusChoice.CLOSE
                )
            ),
            vip_signals_count=models.Count(
                "id",
                filter=models.Q(vip=True)
            ),

            # calculate the absolute value of the ratio between the sum
            # of positive PnLs and the sum of negative PnLs on the query
            risk_to_reward=Cast(
                Abs(models.Sum(models.F("max_pnl_percentage") / models.F("min_pnl_percentage")) / models.Count(
                    'id')),
                output_field=models.DecimalField(max_digits=10, decimal_places=3)
            ),
            # calculate the average number of signals on this service
            # based on the number of weeks since its creation on the query
            avg_weekly_signals=Round(
                models.Count("id") / weeks_since_service_creation,
            ),
            # calculate the average pnl of signals for this service
            avg_pnl_percentage=Cast(
                models.Avg("pnl_percentage"),
                output_field=models.DecimalField(max_digits=10, decimal_places=3)
            ),
            # calcualtes the average open minutes for the signals of this
            # service, open duration timestamp is annotated and the
            # extract expression is used on this annotated field for converting
            # the timestamp to minute
            avg_open_minutes=Round(
                PostgresExtractMinute(models.Avg("open_duration"), output_field=models.FloatField())
            ),
            # caluclates the summation of pnl percentage without considering the
            # percentage of fund
            total_aggregated_pnl_without_pof=Round(
                models.Sum("pnl_percentage")
            )
        )
        pnl_percentage_monthly = base_queryset. \
            annotate(month=models.functions.TruncMonth('closed_datetime')) \
            .values('month') \
            .annotate(
            pnl_percentage=models.Sum('pnl_percentage')
        ).order_by('month').values(
            'month',
            'pnl_percentage'
        )
        result['pnl_percentage_monthly'] = pnl_percentage_monthly
        # append the draw down values from service record directly
        history_type = request.query_params.get("history_type")
        if not history_type:
            history_type = HistoryTypeChoices.WEEKLY
        result['draw_down'] = service.draw_down.get(history_type.upper(), None)
        result['initial_draw_down'] = service.initial_draw_down.get(history_type.upper(), None)
        result['win_rate'] = None
        if result.get('signals_count') != 0:
            result['win_rate'] = int(result.get('closed_signals_pnl_amount_gt_zero_count') * 100 /
                                     result.get('closed_signals_count'))
        return result

    def signal_avg_pnl(self, request, *args, **kwargs):
        base_queryset = self.get_signals_queryset(request.query_params)
        return base_queryset.aggregate(
            in_loss_signal_avg_loss=Abs(
                RoundWithPlaces(
                    models.Avg(
                        F("pnl_percentage"),
                        # TODO: in the right way percentage of fund doesn't affect on pnl percentage,
                        #  It Is affected now, should change the calculate the pnl percentage
                        filter=models.Q(
                            pnl_amount__lt=0
                        ),
                    )
                )),
            profitable_signal_avg_profit=Abs(
                RoundWithPlaces(
                    models.Avg(
                        F("pnl_percentage"),
                        filter=models.Q(
                            pnl_amount__gt=0
                        )
                    )
                )),
            profit_to_loss=Abs(
                Cast(
                    (
                            models.Sum("pnl_percentage", filter=models.Q(
                                pnl_percentage__gt=0
                            )) /
                            models.Sum("pnl_percentage", filter=models.Q(
                                pnl_percentage__lt=0
                            ))
                    ),
                    output_field=models.DecimalField(max_digits=10, decimal_places=3)
                )
            )
        )

    def grouped_signals(self, request, *args, **kwargs):
        base_queryset = self.get_signals_queryset(request.query_params)
        # groups the signals based on the exchange market base currency
        # and aggregate the query to calculate the number of signals and the 
        # average pnl value(performs a join on the exchange market table from signal
        # and a group by on base currency column)
        return base_queryset.values("exchange_market__base_currency") \
            .annotate(
            signals_count=models.Count(
                "exchange_market__base_currency"
            ),
            pnl=models.Sum("pnl_percentage")
        ).order_by("exchange_market__base_currency")

    def grouped_exchanges(self, request, *args, **kwargs):
        base_queryset = self.get_signals_queryset(request.query_params)
        total_signals = float(base_queryset.count())
        # groups the signals based on the exchange name and aggregates
        # the result to calculate the percentage of signals per exchange
        return base_queryset.values("exchange_market__exchange_name") \
            .annotate(
            percentage=Round(
                Cast(
                    models.Count("exchange_market__exchange_name") / total_signals,
                    models.FloatField()
                ) * 100
            )
        ).order_by("exchange_market__exchange_name")


class CopyServiceDashboardMixin:

    def get_positions_queryset(self, query_params):
        service: Service = self.get_object()
        if service.service_type == ServiceTypeChoices.COPY:
            base_queryset = Position.objects.filter(service=service)
            start_time = query_params.get("start_time")
            end_time = query_params.get("end_time")
            history_type = query_params.get("history_type")
            if start_time and end_time:
                return base_queryset.filter(
                    closed_datetime__range=[
                        start_time,
                        end_time,
                    ]
                )
            elif history_type:
                history_type = history_type.upper()
                if history_type not in HistoryTypeChoices.names:
                    raise APIException(
                        "Invalid history type. please select on the following"
                        + ", ".join(HistoryTypeChoices.names)
                    )
                start, end = self.get_history_type_date_range(history_type)
                return base_queryset.filter(
                    closed_datetime__date__range=[start, end]
                )
            else:
                return base_queryset

        raise Http404

    def copy_statistics(self, request, *args, **kwargs):
        weeks_since_service_creation = (
                                               date.today() - self.get_object().created_at.date()
                                       ).days // 7 + 1
        subscriber_ids = Subscription.objects.filter(
            service_id=self.get_object().id,
            is_paid=True
        ).values_list('subscriber__id', flat=True)
        base_queryset = self.get_positions_queryset(request.query_params)
        result = base_queryset \
            .annotate(
            open_duration=(
                    models.F("closed_datetime") - models.F("created_at")
            ),
        ).aggregate(
            positions_count=models.Count("id"),
            closed_positions_count=models.Count(
                "id", filter=models.Q(
                    status=PositionStatusChoices.CLOSED
                )
            ),
            win_positions_count=models.Count(
                            "id",
                            filter=models.Q(
                                closed_pnl_percentage__gt=0,
                                status=PositionStatusChoices.CLOSED
                            )
                        ),
            lose_positions_count=models.Count(
                            "id",
                            filter=models.Q(
                                closed_pnl_percentage__lt=0,
                                status=PositionStatusChoices.CLOSED
                            )
                        ),

            closed_positions_pnl_amount_gt_zero_count=models.Count(
                "id", filter=models.Q(
                    closed_pnl__gt=0,

                    status=PositionStatusChoices.CLOSED
                )
            ),
            avg_weekly_positions=Round(models.Count("id") / weeks_since_service_creation),

            profit_to_loss=RoundWithPlaces(
                Abs(

                    (
                            models.Sum("closed_pnl", filter=models.Q(
                                closed_pnl__gt=0
                            )) /
                            models.Sum("closed_pnl", filter=models.Q(
                                closed_pnl__lt=0
                            ))
                    ),

                )
            ),
            avg_pnl_percentage=RoundWithPlaces(models.Avg("closed_pnl_percentage")),
            avg_open_minutes=PostgresExtractMinute(models.Avg("open_duration")),
            total_pnl_percentage=models.Sum(
                    "closed_pnl_percentage",
                    filter=models.Q(profile=self.get_object().profile)
                )
            ,
            total_subscriber_pnl_percentage=models.Sum(
                    'closed_pnl_percentage',
                    filter=models.Q(profile_id__in=subscriber_ids)
                )
            ,

        )

        result['win_rate'] = None
        if result.get('closed_positions_count') != 0:
            result['win_rate'] = round(result.get('closed_positions_pnl_amount_gt_zero_count') * 100 /
                                       result.get('closed_positions_count'))

        pnl_percentage_monthly = base_queryset.filter(
            closed_datetime__isnull=False
        ) \
            .annotate(month=models.functions.TruncMonth('closed_datetime')) \
            .values('month') \
            .annotate(
            closed_pnl_percentage=models.Sum('closed_pnl_percentage')

        ).order_by('month').values(
            'month',
            'closed_pnl_percentage'
        )
        most_trade = base_queryset.values('symbol').annotate(
            position_count=Count('symbol'),
            pnl=Avg("closed_pnl_percentage")
        ).order_by('-position_count')
        result['pnl_percentage_monthly'] = pnl_percentage_monthly
        result['most_trade'] = most_trade
        result['membership_period'] = (datetime.now() - self.get_object().created_at).days // 30
        result['total_balance'] = self.get_object().balance
        result['win_rate'] = None
        positions = base_queryset.values('closed_pnl_percentage').order_by('created_at')
        max_positives,max_negatives = self.consecutive_counts(positions)
        result['max_positives'] = max_positives
        result['max_negatives'] = max_negatives
        return result

    @staticmethod
    def consecutive_counts(data):
        max_positives = 0
        max_negatives = 0
        curr_positives = 0
        curr_negatives = 0

        for item in data:
            value = item['closed_pnl_percentage']
            if value > 0:
                curr_positives += 1
                curr_negatives = 0
                max_positives = max(max_positives, curr_positives)
            elif value < 0:
                curr_negatives += 1
                curr_positives = 0
                max_negatives = max(max_negatives, curr_negatives)
            else:
                curr_positives = 0
                curr_negatives = 0

        return max_positives, max_negatives

    def copy_avg_pnl(self, request, *args, **kwargs):
        base_queryset = self.get_positions_queryset(request.query_params)
        return base_queryset.aggregate(
            in_loss_position_avg_loss=Abs(
                Round(
                    models.Avg(
                        "closed_pnl_percentage",
                        filter=models.Q(
                            closed_pnl__lt=0
                        )
                    ),
                ),
            ),
            profitable_position_avg_profit=Abs(
                Round(
                    models.Avg(
                        "closed_pnl_percentage",
                        filter=models.Q(
                            closed_pnl__gt=0
                        )
                    ),
                ),
            ),
        )

    def grouped_positions(self, request, *args, **kwargs):
        base_queryset = self.get_positions_queryset(request.query_params)
        return base_queryset.values("symbol") \
            .annotate(
            positions_count=models.Count(
                "symbol"
            ),
            pnl=models.Avg("closed_pnl_percentage")
        ).order_by("symbol")


class ServiceDashboardViewSet(
    GenericViewSet,
    SignalServiceDashboardMixin,
    CopyServiceDashboardMixin,
):
    serializer_class = ServiceReadOnlySerializer
    queryset = Service.objects.all()

    # Open APIs for ananymous or authentication users
    authentication_classes = []
    permission_classes = []

    def get_history_type(self, query_params: QueryDict) -> str:
        history_type = query_params.get(
            "history_type",
            HistoryTypeChoices.WEEKLY
        ).upper()
        if history_type not in HistoryTypeChoices.names:
            raise APIException(
                "Invalid history type. please select on the following"
                + ", ".join(HistoryTypeChoices.names)
            )
        return history_type

    def get_history_type_date_range(self, history_type):
        today = date.today()
        if history_type == HistoryTypeChoices.WEEKLY:
            #  FIXME: temporary using 7 last days, will change
            #  to last week after modify ROIHistory table
            start, end = today - timedelta(weeks=1), today
            # start, end = previous_week_range(today)
        elif history_type == HistoryTypeChoices.TWO_WEEKLY:
            start, end = today - timedelta(days=14), today
        elif history_type == HistoryTypeChoices.MONTHLY:
            #  FIXME: temporary using 30 last days
            #  to last week after modify ROIHistory table
            start, end = today - timedelta(days=30), today
            # start, end = previous_month_range(today)
        elif history_type == HistoryTypeChoices.TWO_MONTHLY:
            start, end = today - timedelta(days=60), today
        elif history_type == HistoryTypeChoices.THREE_MONTHLY:
            #  FIXME: temporary using 120 last days
            #  to last week after modify ROIHistory table
            start, end = today - timedelta(days=90), today
            # start, end = previous_month_range(today)
        elif history_type == HistoryTypeChoices.THREE_MONTHLY:
            #  FIXME: temporary using 120 last days
            #  to last week after modify ROIHistory table
            start, end = today - timedelta(days=90), today
            # start, end = previous_month_range(today)
        return start, end

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'history_type',
                openapi.IN_QUERY,
                description="History type for cumulative pnl report",
                type=openapi.TYPE_STRING
            )
        ]
    )
    @action(methods=["GET"], detail=True)
    def cumulative_roi(
            self,
            request: Request,
            *args,
            **kwargs
    ):
        """
        returns the ROI list for the selected history type on this service
        the values for previous days are queried from database which are 
        calculated on the roi calculation task(per day) and todays value is
        calculated in the runtime
        """
        with get_redis_connection(alias="data_cache") as redis_conn:
            history_type = self.get_history_type(request.query_params)
            key = f"{history_type.upper()}:service_id:{kwargs['pk']}"
            cached_data = redis_conn.get(key)
            if cached_data:
                roi_result = json.loads(cached_data)
            else:
                service = Service.objects.get(id=kwargs['pk'])
                roi_result = cache_roi_and_draw_down(
                    service,
                    3600,
                    history_type,
                    include_current_day=True
                )
        return Response(roi_result['roi_list'], status=HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'history_type',
                openapi.IN_QUERY,
                description="History type for efficiency report",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'start_time',
                openapi.IN_QUERY,
                description="History type for efficiency report",
                type=openapi.FORMAT_DATETIME
            ),
            openapi.Parameter(
                'end_time',
                openapi.IN_QUERY,
                description="History type for efficiency report",
                type=openapi.FORMAT_DATETIME
            ),
        ]
    )
    @action(
        methods=["GET"]
        , detail=True
    )
    def statistics(
            self,
            request,
            *args,
            **kwargs
    ):
        """
        return the statistics of dashboard based on the service type
        """
        service: Service = self.get_object()
        if service.service_type == ServiceTypeChoices.SIGNAL:
            result = self.signal_statistics(request, *args, **kwargs)
        elif service.service_type == ServiceTypeChoices.COPY:
            result = self.copy_statistics(request, *args, **kwargs)
        return Response(result, status=HTTP_200_OK)

    @action(methods=["GET"], detail=True)
    def avg_pnl(self, request, *args, **kwargs):
        """
        return the avg pnl of dashboard based on the service type
        """
        service: Service = self.get_object()
        if service.service_type == ServiceTypeChoices.SIGNAL:
            result = self.signal_avg_pnl(request, *args, **kwargs)
        elif service.service_type == ServiceTypeChoices.COPY:
            result = self.copy_avg_pnl(request, *args, **kwargs)
        return Response(result, status=HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'history_type',
                openapi.IN_QUERY,
                description="History type for risk report",
                type=openapi.TYPE_STRING
            )
        ]
    )
    @action(methods=["GET"], detail=True)
    def risk(self, request, *args, **kwargs):
        """
        calculates the risk for the selected period of time(weekly, monthly, three monthly)
        """
        history_type = self.get_history_type(request.query_params)
        # find the iteration range for the selected history type
        # for example if we need monthly result we need to iterate
        # four times to find four previous weeks date range and data
        if history_type not in HistoryTypeChoices.names or history_type == HistoryTypeChoices.OVERALLY:
            raise APIException(
                "Invalid history type. please select on the following "
                + ", ".join(HistoryTypeChoices.names[:-2])
            )
        elif history_type == HistoryTypeChoices.WEEKLY:
            iteration_range = 1
        elif history_type == HistoryTypeChoices.TWO_WEEKLY:
            iteration_range = 2
        elif history_type == HistoryTypeChoices.MONTHLY:
            iteration_range = 4
        elif history_type == HistoryTypeChoices.TWO_MONTHLY:
            iteration_range = 8
        elif history_type == HistoryTypeChoices.THREE_MONTHLY:
            iteration_range = 12

        result = []
        today = date.today()
        for i in range(iteration_range):
            # find the start and end date of previous weeks for the period

            start, end = previous_week_range(today)
            # query the minimum value of pnl percentage in the selected week range
            # and map the pnl based on the risk factor
            signal_count = TradingSignal.objects.filter(
                sid_id=kwargs.get('pk'),
                closed_datetime__range=[start, end]
            ).count()
            if signal_count == 0:
                risk = math.inf
            else:
                risk = DailyAggregatedPnl.objects.filter(
                    date__range=[start, end],
                    service_id=kwargs["pk"],
                ) \
                    .aggregate(
                    risk=Coalesce(
                        models.Min("percentage"),
                        math.inf,
                        output_field=models.FloatField()
                    )
                )["risk"]
            result.append(
                dict(
                    date=end,
                    value=risk_evaluation(
                        abs(risk)
                    )
                )
            )
            today = today - timedelta(days=7)
        return Response(result, status=HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'history_type',
                openapi.IN_QUERY,
                description="History type for efficiency report",
                type=openapi.TYPE_STRING
            )
        ]
    )
    @action(methods=["GET"], detail=True)
    def efficiency(self, request, *args, **kwargs):
        history_type = self.get_history_type(request.query_params)
        if history_type == HistoryTypeChoices.WEEKLY:
            iteration_range = 1
        elif history_type == HistoryTypeChoices.TWO_WEEKLY:
            iteration_range = 2
        elif history_type == HistoryTypeChoices.MONTHLY:
            iteration_range = 4
        elif history_type == HistoryTypeChoices.TWO_MONTHLY:
            iteration_range = 8
        elif history_type == HistoryTypeChoices.THREE_MONTHLY:
            iteration_range = 12

        result = []
        today = date.today()
        for i in range(iteration_range):
            start, end = previous_week_range(today)
            # aggregate the pnl for the selected week date range
            efficiency = DailyAggregatedPnl.objects.filter(
                date__range=[start, end],
                service_id=kwargs["pk"],
            ) \
                .aggregate(
                efficiency=Coalesce(
                    models.Sum("percentage"),
                    0,
                    output_field=models.FloatField()
                )
            )["efficiency"]
            result.append(dict(date=end, value=efficiency))
            today = today - timedelta(days=7)
        return Response(result, status=HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'history_type',
                openapi.IN_QUERY,
                description="History type for exchanges pie report",
                type=openapi.TYPE_STRING
            )
        ]
    )
    @action(methods=["GET"], detail=True)
    def exchanges(self, request, *args, **kwargs):
        result = self.grouped_exchanges(request, *args, **kwargs)
        return Response(result, status=HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'history_type',
                openapi.IN_QUERY,
                description="History type for signals pie report",
                type=openapi.TYPE_STRING
            )
        ]
    )
    @action(methods=["GET"], detail=True)
    def signals(self, request, *args, **kwargs):
        result = self.grouped_signals(request, *args, **kwargs)
        return Response(result, status=HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'history_type',
                openapi.IN_QUERY,
                description="History type for aggregated table",
                type=openapi.TYPE_STRING
            )
        ]
    )
    @action(methods=["GET"], detail=True)
    def aggregated_pnl(self, request, *args, **kwargs):
        history_type = self.get_history_type(request.query_params)
        start, end = self.get_history_type_date_range(history_type)
        return Response(
            DailyAggregatedPnl.objects.filter(
                date__range=[start, end],
                service_id=kwargs["pk"],
            ).values("date", "percentage", "amount","v_balance","v_balance_change").order_by('-date'),
            status=HTTP_200_OK,
        )

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'history_type',
                openapi.IN_QUERY,
                description="History type for subscribers chart",
                type=openapi.TYPE_STRING
            )
        ]
    )
    @action(methods=["GET"], detail=True)
    def users(self, request: Request, *args, **kwargs):
        # aggregates the subscribers of selected service grouped by
        # the month of years
        history_type = self.get_history_type(request.query_params)
        start, end = self.get_history_type_date_range(history_type)
        days_list = days_between_dates(start, end)
        result = []
        # TODO: create a task and update daily later
        for day in days_list:
            service = Service.objects.annotate(
                vip_count=SubqueryCount(
                    Subscription.objects.filter(
                        service_id=OuterRef("pk"),
                        created_at__lte=day + timedelta(days=1),  # To involve today in filter
                        is_paid=True,
                        expire_time__gte=day
                    ).order_by('subscriber_id').distinct('subscriber_id')
                ),
                follower_count=SubqueryCount(
                    VendorFollower.objects.filter(
                        vendor__services__id=OuterRef("pk"),
                        created_at__lte=day + timedelta(days=1),  # To involve today in filter
                    )
                )
            ).get(pk=kwargs["pk"])
            result.append(
                dict(day=day, follower_count=service.follower_count, vip_count=service.vip_count)
            )

        return Response(
            result,
            status=HTTP_200_OK
        )

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'history_type',
                openapi.IN_QUERY,
                description="History type for subscribers chart",
                type=openapi.TYPE_STRING
            )
        ]
    )
    @action(methods=["GET"], detail=True)
    def positions(self, request: Request, *args, **kwargs):
        result = self.grouped_positions(request, *args, **kwargs)
        return Response(result, status=HTTP_200_OK)
