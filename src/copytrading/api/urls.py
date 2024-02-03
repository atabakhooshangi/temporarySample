from django.urls import path, include
from rest_framework.routers import DefaultRouter

from copytrading.api.views import (
    CopyTradingViewSet,
    ExchangeBalanceAPIView,
    TradingOrderHistoryViewSet,
    UserCopyServiceAPIView,
    UserCopyServiceHistoryAPIView,
    CopySettingAPIView,
    ServicePositionHistoryAPIView,
    ServiceTradingOrderHistoryAPIView,
    ClosePositionAPIView,
    UserCopyServiceDashboardAPIView,
    EditPositionAPIView
)
from copytrading.api.views.order import CancelOrderAPIView
from copytrading.api.views.position import PositionListViewSet, MyCopiedPositions, CreatePnlHistoryForVendor

router = DefaultRouter()
router.register(
    prefix="",
    viewset=CopyTradingViewSet,
    basename="copy_trading",
)
router.register(
    prefix="order_history",
    viewset=TradingOrderHistoryViewSet,
    basename="user_order_history",
)

urlpatterns = [
    path('', include(router.urls)),
    path(
        'exchanges/<str:exchange>/<str:coin>/balance/',
        ExchangeBalanceAPIView.as_view(),
        name="exchange_balance",
    ),
    path(
        'services/<int:pk>/setting/',
        CopySettingAPIView.as_view(),
        name="copy_setting",
    ),
    path(
        'copy_services/',
        UserCopyServiceAPIView.as_view(),
        name="copy_services",
    ),
    path(
        'copy_services/<int:pk>/dashboard/',
        UserCopyServiceDashboardAPIView.as_view(),
        name="copy_service_dashboard",
    ),
    path(
        'copy_history/',
        UserCopyServiceHistoryAPIView.as_view(),
        name="copy_history",
    ),
    path(
        'service/<int:pk>/position_history/',
        ServicePositionHistoryAPIView.as_view(),
        name="service_position_history",
    ),
    path(
        'service/<int:pk>/order_history/',
        ServiceTradingOrderHistoryAPIView.as_view(),
        name="service_position_history",
    ),
    path(
        'my-positions/',
        PositionListViewSet.as_view(),
        name="my_positions"
    ),
    path(
        'my-copied-positions/',
        MyCopiedPositions.as_view(),
        name="my_copied_positions"
    ),
    path(
        'positions/<int:pk>/close',
        ClosePositionAPIView.as_view(),
        name="close_position"
    ),
    path(
        'positions/<int:pk>/edit',
        EditPositionAPIView.as_view(),
        name="edit_position"
    ),
    path(
        'order/<int:pk>/cancel',
        CancelOrderAPIView.as_view(),
        name="cancel_order"
    ),
path(
        'positions/fetch_history',
        CreatePnlHistoryForVendor.as_view(),
        name="fetch_history"
    )
]
