from rest_framework import serializers

from invitation.serializers.invitation_code import InvitationCodeSerializer


class InvitationReferralSerializer(serializers.Serializer):
    referral_code = serializers.CharField()
    owner_id = serializers.IntegerField(write_only=True)
    invitation_code = InvitationCodeSerializer(read_only=True)
    seen = serializers.BooleanField(read_only=True)
