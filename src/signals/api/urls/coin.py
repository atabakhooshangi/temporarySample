from django.urls import path, include
from rest_framework.routers import DefaultRouter

from signals.api.views import CoinDecimalNumberConfigView

router = DefaultRouter()

urlpatterns = [
    path('decimal_number',
         CoinDecimalNumberConfigView.as_view(),
         name='decimal_number'
         ),
    path('config', include(router.urls)),
]
