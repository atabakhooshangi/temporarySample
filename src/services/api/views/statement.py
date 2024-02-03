import json
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from django.db import models
from django.db.models import OuterRef, Value, Subquery, Q
from django.db.models.functions import Cast, Round, Abs
from django.http import Http404, QueryDict
from django_redis import get_redis_connection
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.viewsets import GenericViewSet

from core.base_view import MultiplePaginationViewMixin
from core.choice_field_types import HistoryTypeChoices, StatusChoice, ServiceTypeChoices
from core.pagination import CustomPaginator, MultiplePaginationMixin
from core.sql_functions import PostgresExtractMinute, SubqueryCount, SubqueryAvg, SubquerySum
from services.cache_utils import cache_roi_and_draw_down
from services.exceptions import ServiceIsNotFound
from services.models import Service, DailyAggregatedPnl, ROIHistory, DailyROI
from services.serializers.statement import TraderStatementReadOnlySerializer, SignalStatementHistorySerializer
from services.utils import calculate_maximum_draw_down
from signals.models import TradingSignal
from user.models import Profile


class SignalServiceStatement:

    def base_signal_queryset(self, service_id, history_type):
        base_queryset = TradingSignal.objects.filter(sid=service_id)
        start, end = self.get_history_type_date_range(history_type)
        return base_queryset.filter(
            closed_datetime__date__range=[start, end]
        )

    @staticmethod
    def get_roi_history(service: Service, history_type):
        with get_redis_connection(alias="data_cache") as redis_conn:
            today = date.today()
            key = f"{history_type.upper()}:service_id:{service.id}"
            cached_data = redis_conn.get(key)
            if cached_data:
                final_result = json.loads(cached_data)
            else:
                final_result = cache_roi_and_draw_down(service, 3600, history_type, include_current_day=True)
            roi_percentages = [roi["percentage"] for roi in final_result['roi_list']]
            draw_down = calculate_maximum_draw_down(roi_percentages)
            if len(final_result['roi_list']) == 0:
                return [], draw_down, today
            return final_result['roi_list'][-1], draw_down, today

    def get_signal_data(self, *args, **kwargs):

        base_qset = self.base_signal_queryset(kwargs['service_id'], history_type=kwargs['history_type'])
        result = base_qset.aggregate(
            closed_signals_count=models.Count(
                "id", filter=models.Q(
                    state=StatusChoice.CLOSE
                )
            ),
            closed_signals_pnl_amount_gt_zero_count=models.Count(
                "id",
                filter=models.Q(
                    pnl_amount__gt=0,
                    state=StatusChoice.CLOSE,
                )
            )
        )
        result['win_rate'] = None
        if result.get('closed_signals_count') != 0:
            result['win_rate'] = round(result.get('closed_signals_pnl_amount_gt_zero_count') * 100 /
                                       result.get('closed_signals_count'))
        return result


class CopyServiceStatement:
    def get_copy_statement(self, *args, **kwargs):
        pass


class StatementViewSet(GenericViewSet,
                       mixins.ListModelMixin,
                       SignalServiceStatement,
                       CopyServiceStatement,
                       MultiplePaginationViewMixin):
    pagination_class = MultiplePaginationMixin

    def get_paginated_response(self, data):
        if self.action == 'list':
            return super(StatementViewSet, self).get_paginated_response(data)

        return data

    def get_signal_history(self):
        try:
            history_type = self.get_history_type(self.request.query_params)
            start, end = self.get_history_type_date_range(history_type)
            return TradingSignal.objects.filter(
                sid=self.kwargs.get('pk'),
                entry_point_hit_datetime__isnull=False,
                closed_datetime__date__range=[start, end]
            ).select_related(
                'exchange_market'
            ).order_by('-closed_datetime')
        except Service.DoesNotExist:
            raise ServiceIsNotFound

    def get_queryset(self):
        if self.action == 'list':
            return self.get_signal_history()
        # useless but for later use maybe
        return Service.objects.all()

    def get_serializer_class(self):
        if self.action == 'trader_statement':
            return TraderStatementReadOnlySerializer
        if self.action == 'list':
            return SignalStatementHistorySerializer
        return super().get_serializer_class()

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'history_type',
                openapi.IN_QUERY,
                description="History type for efficiency report",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'page_size',
                openapi.IN_QUERY,
                description="page size",
                type=openapi.TYPE_STRING
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super(StatementViewSet, self).list(request, *args, **kwargs)

    @staticmethod
    def get_object(**kwargs):
        return Service.objects.get(id=kwargs['service_id'], service_type=kwargs['service_type'])

    def get_history_type_date_range(self, history_type):
        today = date.today()
        if history_type == HistoryTypeChoices.WEEKLY:
            #  FIXME: temporary using 7 last days, will change
            #  to last week after modify ROIHistory table
            start, end = today - timedelta(weeks=1), today
            # start, end = previous_week_range(today)
        elif history_type == HistoryTypeChoices.MONTHLY:
            #  FIXME: temporary using 30 last days
            #  to last week after modify ROIHistory table
            start, end = today - timedelta(days=30), today
            # start, end = previous_month_range(today)
        elif history_type == HistoryTypeChoices.THREE_MONTHLY:
            #  FIXME: temporary using 120 last days
            #  to last week after modify ROIHistory table
            start, end = today - timedelta(days=120), today
            # start, end = previous_month_range(today)
        elif history_type == HistoryTypeChoices.OVERALLY:
            start, end = today - relativedelta(years=5), today
        return start, end

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

    @staticmethod
    def get_profile(owner_id) -> dict:
        profile: Profile = Profile.objects.filter(owner_id=owner_id).values('username', 'title').first()
        return profile

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'history_type',
                openapi.IN_QUERY,
                description="History type for efficiency report",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'service_type',
                openapi.IN_QUERY,
                description="Service Type (signal , copy)",
                type=openapi.TYPE_STRING
            )
        ]
    )
    @action(
        methods=["GET"]
        , detail=True
    )
    def social_statement(
            self,
            request,
            *args,
            **kwargs
    ):
        service_type = request.query_params.get('service_type')
        if service_type == 'copy':
            return Response(data={}, status=HTTP_200_OK)
        service: Service = self.get_object(service_id=kwargs['pk'], service_type=ServiceTypeChoices.SIGNAL)
        profile = self.get_profile(self.request.user.owner_id)
        history_type = self.get_history_type(request.query_params)
        signal_statement = self.get_signal_data(service_id=service.id, history_type=history_type)
        roi, max_draw_down, today = self.get_roi_history(service, history_type)
        result = {
            "username": profile['username'],
            "title": profile['title'],
            "roi": roi,
            "date": today,
            "win_rate": signal_statement['win_rate'],
            "signal_count": signal_statement['closed_signals_count'],
            "draw_down": max_draw_down
        }
        return Response(result, HTTP_200_OK)

    def get_trader_st_queryset(self, **kwargs):
        start, end = self.get_history_type_date_range(kwargs['query_history'])
        queryset = Service.objects.filter(
            is_visible=True,
            service_type=ServiceTypeChoices.SIGNAL
        ).select_related(
            "profile",
        ).prefetch_related(
            "service_signals",
            "roi_history_services",
            "roi_history_services__rois"
        ).annotate(
            start_date=Value(start, output_field=models.DateTimeField()),
            end_date=Value(end, output_field=models.DateTimeField()),

            # find the number of closed signals on this service
            closed_signals_count=SubqueryCount(
                TradingSignal.objects.filter(
                    Q(sid_id=models.OuterRef("id")) &
                    Q(state=StatusChoice.CLOSE) &
                    Q(closed_datetime__date__range=[start, end])
                )
            ),
            # calculate the win rate of service, using when case
            # for returning null values when there are no closed signals
            # and using subquery
            win_rate=Round(
                models.Case(
                    models.When(
                        closed_signals_count=0,
                        then=models.Value(None)
                    ),
                    default=Cast(
                        SubqueryCount(
                            TradingSignal.objects.filter(
                                models.Q(
                                    sid_id=models.OuterRef("id")) &
                                models.Q(pnl_amount__gt=0) &
                                models.Q(
                                    closed_datetime__date__range=[start, end]) &
                                models.Q(
                                    closed_datetime__isnull=False) &
                                models.Q(
                                    state=StatusChoice.CLOSE)

                            )
                        ) * 100 / models.F("closed_signals_count"),
                        output_field=models.FloatField()
                    ),
                ),
            ),

            # find the total number of signals using a subquery count expression
            signal_count=SubqueryCount(
                TradingSignal.objects.filter(sid_id=models.OuterRef("id"),
                                             closed_datetime__date__range=[
                                                 start, end])

            ),
            # find the last percentage value of service roi using
            # a subquery expression on services daily rois(sorts with number
            # to get the last record)
            cost_and_benefit=Subquery(
                DailyROI.objects.filter(roi_history__service_id=OuterRef('id'),
                                        roi_history__history_type=kwargs['query_history']).order_by(
                    '-number').values_list('percentage')[:1]
            )
            ,
            avg_open_minutes=PostgresExtractMinute(SubqueryAvg(
                TradingSignal.objects.filter(sid_id=models.OuterRef("id"),
                                             closed_datetime__date__range=[
                                                 start, end]).annotate(
                    open_duration=(models.F("closed_datetime") - models.F("start_datetime"))).values('open_duration'),
                'open_duration', models.CharField()))
            ,
            profit_to_loss=Abs(
                Round(
                    (
                            SubquerySum(TradingSignal.objects.filter(sid_id=models.OuterRef("id"),
                                                                     pnl_percentage__gt=0,
                                                                     closed_datetime__date__range=[
                                                                         start, end]), 'pnl_percentage') /
                            SubquerySum(TradingSignal.objects.filter(sid_id=models.OuterRef("id"),
                                                                     pnl_percentage__lt=0,
                                                                     closed_datetime__date__range=[
                                                                         start, end]), 'pnl_percentage')
                    ),
                )
            ),
            avg_pnl_percentage=SubqueryAvg(
                TradingSignal.objects.filter(sid_id=models.OuterRef("id"),
                                             closed_datetime__date__range=[
                                                 start, end])
                , 'pnl_percentage')

        ).filter(profile__owner_id=kwargs['owner_id']).first()

        return queryset

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'history_type',
                openapi.IN_QUERY,
                description="History type for efficiency report",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'service_type',
                openapi.IN_QUERY,
                description="Service Type (signal , copy)",
                type=openapi.TYPE_STRING
            )
        ]
    )
    @action(
        methods=["GET"]
        , detail=False
    )
    def trader_statement(
            self,
            request,
            *args,
            **kwargs
    ):
        service_type = request.query_params.get('service_type')
        if service_type == 'copy':
            return Response(data={}, status=HTTP_200_OK)

        history_type = self.get_history_type(request.query_params)
        queryset = self.get_trader_st_queryset(owner_id=request.user.owner_id, query_history=history_type)
        serializer = self.get_serializer(queryset, context={"history": history_type})

        return Response(serializer.data, HTTP_200_OK)
