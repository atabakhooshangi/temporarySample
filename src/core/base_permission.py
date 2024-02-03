from rest_framework.permissions import BasePermission


from core.choice_field_types import AuthenticationLevelChoices
from core.base_exception import (
    LevelOneAuthenticationRequiredException,
    LevelTwoAuthenticationRequiredException
)
from user.models import IAMUser


class LevelOneAuthenticationRequiredPermission(BasePermission):
    def has_permission(self, request, view):
        user: IAMUser = request.user
        if user.authentication_level not in (
            AuthenticationLevelChoices.LEVEL_ONE,
            AuthenticationLevelChoices.LEVEL_TWO
        ):
            raise LevelOneAuthenticationRequiredException
        return True


class LevelTwoAuthenticationRequiredPermission(BasePermission):
    def has_permission(self, request, view):
        user: IAMUser = request.user
        if not (user.authentication_level == AuthenticationLevelChoices.LEVEL_TWO):
            raise LevelTwoAuthenticationRequiredException
        return True
