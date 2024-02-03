from rest_framework import status
from rest_framework.mixins import DestroyModelMixin
from rest_framework.response import Response


class CustomDestroyModelMixin(DestroyModelMixin):
    """
    Destroy a model instance.
    """
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        if hasattr(instance, 'is_deleted'):
            instance.is_deleted = True
            instance.save()
        else:
            instance.delete()
