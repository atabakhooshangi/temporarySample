from rest_framework import serializers

from core.base_model import BaseModelClass


class BaseModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaseModelClass
