from django.urls import path, include
from rest_framework.routers import DefaultRouter

from services.api.views import (
    CoinModelViewSet,
    ServiceViewList,
    ServiceCreateViewSet,
    SignalServiceViewList,
    ServiceDashboardViewSet,
    PaymentGatewayRedirectAPIView,
    SubscriptionInvoiceIPGVerifyAPIView,
    SubscriptionViewSet,
    SubscriptionInvoiceViewSet,
    PositionServiceViewList,
    CalculationViewset,
    StatementViewSet
)
from services.api.views.service import (
    ExchangeListViewSet,
    ServiceUpdateViewSet,
    ServiceRankListViewSet,
    TradingOrderServiceViewList,
    OpenPositionServiceViewList,
    CopyServiceViewList,
    CopyServiceAnalysisViewSet, USDTPriceView
)
from signals.api.views import ExchangeMarketListView

router = DefaultRouter()
# user routes


router.register(
    prefix="coins",
    viewset=CoinModelViewSet,
    basename="coin"
)
router.register(
    prefix='calculation',
    viewset=CalculationViewset,
    basename='calculation'
)

router.register(
    prefix="invoices",
    viewset=SubscriptionInvoiceViewSet,
    basename="subscription_invoice"
)
router.register(
    prefix="subscriptions",
    viewset=SubscriptionViewSet,
    basename="subscription"
)
router.register(
    prefix="dashboard",
    viewset=ServiceDashboardViewSet,
    basename="service_dashboard"
)
router.register(
    prefix="",
    viewset=ServiceViewList,
    basename="service"
)

router.register(
    prefix='statement',
    viewset=StatementViewSet,
    basename="statements"
)

router.register(
    prefix='copy-service',
    viewset=CopyServiceAnalysisViewSet,
    basename="copy_services"
)
# base services route

urlpatterns = [
    path(
        '<int:pk>/signal-history-statement/',
        StatementViewSet.as_view({'get': 'list'}),
        name='statements'
    ),
    path(
        '',
        ServiceViewList.as_view({'get': 'list'}),
        name='service'
    ),
    path(
        'copy/',
        CopyServiceViewList.as_view({'get': 'list'}),
        name='copy-service'
    ),
    path(
        'copy/<int:pk>/',
        CopyServiceViewList.as_view({'get': 'retrieve'}),
        name='copy-service-detail'
    ),
    path(
        '<int:pk>/signals',
        SignalServiceViewList.as_view({'get': 'list'}),
        name='signals'
    ),
    path(
        '<int:pk>/orders',
        TradingOrderServiceViewList.as_view({'get': 'list'}),
        name='orders'
    ),
    path(
        '<int:pk>/positions',
        PositionServiceViewList.as_view({'get': 'list'}),
        name='positions'
    ),
    path(
        '',
        ServiceCreateViewSet.as_view({'post': 'create'}),
        name='service_create'
    ),
    path(
        '<int:pk>/signals/<int:signal_id>',
        SignalServiceViewList.as_view({'get': 'retrieve'}),
        name='signals_r'
    ),
    path(
        '<int:pk>',
        ServiceUpdateViewSet.as_view({'patch': 'partial_update'}),
        name='update-service'
    ),
    path(
        'invoices/pay/',
        PaymentGatewayRedirectAPIView.as_view(),
        name='ipg_redirect'
    ),
    path(
        'invoices/verify/',
        SubscriptionInvoiceIPGVerifyAPIView.as_view(),
        name='invoice_verify',
    ),
    path(
        'exchange',
        ExchangeListViewSet.as_view({'get': 'list'}),
        name='exchange-list'
    ),
    path(
        '<int:pk>/exchange-market',
        ExchangeMarketListView.as_view({'get': 'list'}),
        name='exchange-market'
    ),
    path(
        'ranking',
        ServiceRankListViewSet.as_view({'get': 'list'}),
        name='ranking'
    ),
    path(
        '<int:pk>/open-positions',
        OpenPositionServiceViewList.as_view({'get': 'list'}),
        name='open_position'
    ),
    path(
        'wx-usdt-price',
        USDTPriceView.as_view(),
        name='signals_r'
    ),
    path('', include(router.urls)),
]
