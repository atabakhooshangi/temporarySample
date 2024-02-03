from django.conf import settings
from rest_framework.permissions import BasePermission


class InternalApiKeyPermission(BasePermission):
    @staticmethod
    def _has_permission(request):
        header_api_key = request.META.get('HTTP_X_SOCIAL_KEY', None)
        if header_api_key is None:
            return False
        if header_api_key == settings.SOCIAL_API_KEY:
            return True
        return False

    def has_permission(self, request, view):
        return self._has_permission(request)

    def has_object_permission(self, request, view, obj):
        return self._has_permission(request)
