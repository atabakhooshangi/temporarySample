from django.urls import path, include
from rest_framework.routers import DefaultRouter

from signals.api.views import (
    SignalTradingViewSet,
    CommentViewSet,
    ExchangeMarketListView,
    CryptoLivePriceAPIView,
    FreeSignalListView,
    VirtualBalanceAPIView
)
from signals.api.views.signal import SignalQuickActionViewSet, QuickActionPositionViewSet, QuickActionOrderViewSet

router = DefaultRouter()

router.register(
    prefix='',
    viewset=SignalTradingViewSet,
    basename='signal'
)

router.register(
    prefix='virtual',
    viewset=VirtualBalanceAPIView,
    basename='virtual_balance'
)

urlpatterns = [
    path(
        'quick-action',
        SignalQuickActionViewSet.as_view({'post': 'create'}),
        name='quick-action'
    ),
    path(
        'quick-action/order',
        QuickActionOrderViewSet.as_view({
            'get': 'list'
        }),
        name='quick-action-order'
    ),
    path(
        'quick-action/<int:pk>/order',
        QuickActionOrderViewSet.as_view({
            'put': 'update'
        }),
        name='quick-action-update_order'
    ),
    path(
        'quick-action/order/<int:pk>/cancel',
        QuickActionOrderViewSet.as_view({
            'get': 'cancel'
        }),
        name='quick-action-cancel-order'
    ),
    path(
        'quick-action/position',
        QuickActionPositionViewSet.as_view({
            'get': 'list'
        }),
        name='quick-action-position'
    ),
    path(
        'quick-action/<int:pk>/position',
        QuickActionPositionViewSet.as_view({
            'put': 'update'
        }),
        name='quick-action-update_position'
    ),
    path(
        'quick-action/position/<int:pk>/close',
        QuickActionPositionViewSet.as_view({
            'get': 'close'
        }),
        name='quick-action-close-position'
    ),
    path(
        'free/',
        FreeSignalListView.as_view({'get': 'list'}),
        name='all-signal'
    ),
    path(
        '<int:pk>/comment',
        CommentViewSet.as_view(
            {
                'post': 'create',
                'get': 'list'
            }
        ),
        name='comment'
    ),
    path(
        'comment/<int:pk>/reply',
        CommentViewSet.as_view({'post': 'reply'}),
        name='reply-comment'
    ),
    path(
        'exchange-market',
        ExchangeMarketListView.as_view({'get': 'list'}),
        name='exchange-market'
    ),  # TODO: I think is not required
    path(
        'exchange-market/me',
        ExchangeMarketListView.as_view({'get': 'me'}),
        name='exchange-market-me'
    ),
    path(
        'live_price/',
        CryptoLivePriceAPIView.as_view(),
        name='live_price'
    ),
    path('', include(router.urls)),
]
