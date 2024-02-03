from rest_framework.permissions import BasePermission

from signals.models import SignalVirtualBalance


class IsVirtualBalanceOwner(BasePermission):

    def has_object_permission(self, request, view, obj: SignalVirtualBalance):
        return obj.service.profile.owner_id == request.user.owner_id