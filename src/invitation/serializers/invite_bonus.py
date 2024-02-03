import os

from django.conf import settings
from django.db.transaction import atomic
from django.http import Http404
from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from invitation.models import InviteBonus


class InviteBonusListSerializer(serializers.ModelSerializer):
    class Meta:
        model = InviteBonus
        fields = ['id', 'subscriber_iam_id', 'inviter_id', 'created_at']


class FillInvitersSerializer(serializers.Serializer):
    inviter_subscriber_data = serializers.DictField(required=True)
    ref_code_data = serializers.DictField(required=True)

    # @atomic
    def save(self, **kwargs):
        data: dict = self.validated_data['inviter_subscriber_data']
        referral_data = self.validated_data['ref_code_data']
        for k, v in data.items():
            try:
                invite_obj: InviteBonus = get_object_or_404(InviteBonus, subscriber_iam_id=int(k))

                invite_obj.inviter_id = int(v)
                if int(v) != 0:
                    invite_obj.inviter_referral_code = referral_data[k]
                    invite_obj.amount = settings.INVITER_FEE
                else:
                    invite_obj.amount = 0
                invite_obj.save()
            except Http404:
                continue
            except Exception as e:
                raise e
                print(e)
                raise serializers.ValidationError(e.args)

        return 200


class InviteBonusSumSerializer(serializers.Serializer):
    invite_sum = serializers.FloatField(default=0.0)
    inviter_referral_code = serializers.CharField(allow_null=True)
