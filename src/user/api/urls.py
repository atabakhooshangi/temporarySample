from django.urls import path, include
from rest_framework.routers import DefaultRouter

from user.api.views import (
    ProfileViewSet
)
from user.api.views.profile import ApiKeyViewSet

router = DefaultRouter()
router.register(
    prefix='api-key',
    viewset=ApiKeyViewSet,
    basename='api-key'
)

urlpatterns = [
    path('', ProfileViewSet.as_view({
        'get': 'retrieve',
        'post': 'create',
        'put': 'update',
        'patch': 'partial_update',
    }),
         name="profile"
         ),
    path('vendor', ProfileViewSet.as_view({
        'put': 'vendor',
    }),
         name="profile-vendor"
         ),
    path('subscribed_services/', ProfileViewSet.as_view({
        'get': 'subscribed_services',
    }),
         name="subscribed-services"
         ),
    path('vendor/subscriber', ProfileViewSet.as_view({
        'get': 'vendor_subscriber'
    }),
         name='vendor-subscriber'),
    path('', include(router.urls)),
]
