from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.permissions import BasePermission

from core.choice_field_types import ServiceStateChoices
from services.models import Service
from user.models import Profile


class UpdateServicePermission(BasePermission):
    @staticmethod
    def _has_permission(request, view):
        if Service.objects.get(id=view.kwargs.get('pk')).profile.owner_id == request.user.owner_id:
            return True
        return False

    def has_permission(self, request, view):
        return self._has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        return self._has_permission(request, view)


class RankingServicePermission(BasePermission):
    @staticmethod
    def _has_permission(request, view):
        if Service.objects.filter(~Q(state=ServiceStateChoices.PUBLISH),
                                  Q(profile__owner_id=request.user.owner_id)).exists():
            return True
        return False

    def has_permission(self, request, view):
        return self._has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        return self._has_permission(request, view)


class UserIsServiceOwnerPermission(BasePermission):

    def has_object_permission(self, request, view, obj: Service):
        return obj.profile.owner_id == request.user.owner_id



