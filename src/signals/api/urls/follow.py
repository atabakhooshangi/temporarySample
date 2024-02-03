from django.urls import path

from signals.api.views import follow

urlpatterns = [
    path('', follow.FollowViewSet.as_view({'post': 'create'}),
         name='follow'),
    path('<int:pk>/', follow.FollowViewSet.as_view({'delete': 'destroy'}),
         name='unfollow'),
    path(
        '<int:pk>/follower',
        follow.FollowViewSet.as_view({'get': 'follower'}),
        name='follower'
    ),
    path(
        '<int:pk>/following',
        follow.FollowViewSet.as_view({'get': 'following'}),
        name='following'
    ),

]
