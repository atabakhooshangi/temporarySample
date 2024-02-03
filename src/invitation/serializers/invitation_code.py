from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated

from invitation.models import InvitationCode
from invitation.models.invitation_code import AssigneeEntities
from services.models import Service


class AssigneeEntitiesSerializer(serializers.Serializer):
    assignee_id = serializers.ListSerializer(
        child=serializers.IntegerField(),
    )


class InvitationCodeSerializer(serializers.ModelSerializer):
    assignee_entities = AssigneeEntitiesSerializer(many=True, read_only=True)

    class Meta:
        model = InvitationCode
        fields = [
            'id',
            'code_string',
            'owner_id',
            'description',
            'assignor_type',
            'assignee_entities',
            'invitation_type',
            'invitation_amount',
            'user_limit',
            'start_date',
            'expire_date',

        ]

    def validate(self, value):
        assignee_entities = self.context['request'].data.get('assignee_entities', [])
        if not assignee_entities:
            raise serializers.ValidationError("Assignee entities are required")
        if assignee_entities == [0]:
            return value
        service_ids = Service.objects.filter(id__in=assignee_entities).values_list('id', flat=True)
        diff = set(assignee_entities) - set(service_ids)
        if diff:
            raise serializers.ValidationError(f"Service with ids {diff} does not exist")
        return value
