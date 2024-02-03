from django.urls import path, include
from rest_framework.routers import DefaultRouter
from invitation.api.views import InviteBonusViewSet
from invitation.api.views.invitation_code import InvitationCodeViewSet
from invitation.api.views.invitation_referral import InvitationReferralView

router = DefaultRouter()

router.register(
    prefix="invite-bonus",
    viewset=InviteBonusViewSet,
    basename="invite-bonus"
)

urlpatterns = [
    path(
        'fill-inviters/',
        InviteBonusViewSet.as_view({'post': 'fill_inviters'}),
        name='fill_inviters'
    ),
    # path(
    #     'invitation-code/',
    #     InvitationCodeViewSet.as_view(),
    # ),
    # path(
    #     'invitation-code/exists/',
    #     InvitationCodeViewSet.as_view({'post': 'exists'}),
    # ),
    # path(
    #     'invitation-code/<int:pk>/',
    #     InvitationCodeViewSet.as_view({'get': 'retrieve'}),
    # ),
    path(
        'invitation-code/',
        InvitationCodeViewSet.as_view({'post': 'create'}),
    ),
    path(
        'invitation-code/check/<str:code>/<int:service_id>/',
        InvitationCodeViewSet.as_view({'get': 'check'}),
    ),
    path(
        'inviter-sum/',
        InviteBonusViewSet.as_view({'get': 'inviter_sum'}),
        name='inviter_sum'
    ),
    path(
        'referral-invitee/',
        InvitationReferralView.as_view(),
        name='referral-invitee'
    ),
    path('', include(router.urls)),
]

