from rest_framework.permissions import BasePermission

from copytrading.models import CopySetting, ApiKey, Position


class IsCopySettingOwnerPermission(BasePermission):

    def has_object_permission(self, request, view, obj: CopySetting):
        return obj.profile.owner_id == request.user.owner_id


class IsApiKeyOwnerPermission(BasePermission):

    def has_object_permission(self, request, view, obj: ApiKey):
        return obj.owner.owner_id == request.user.owner_id


class IsVendorAndIsOwner(BasePermission):
    def has_object_permission(self, request, view, obj: Position):
        return (obj.profile.owner_id == request.user.owner_id) and (
                obj.service.profile.owner_id == request.user.owner_id)
