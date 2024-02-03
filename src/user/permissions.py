from django.shortcuts import get_object_or_404
from rest_framework.permissions import BasePermission

from user.models import Profile


class IsVendorPermission(BasePermission):
    def has_permission(self, request, view):
        user = get_object_or_404(
            Profile,
            owner_id=request.user.owner_id
        )
        return user.is_vendor
