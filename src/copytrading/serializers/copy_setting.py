from rest_framework.serializers import ModelSerializer
from copytrading.models import CopySetting


class CopySettingModelSerializer(ModelSerializer):

    class Meta:
        model = CopySetting
        fields = (
            "id",
            "margin",
            "take_profit_percentage",
            "stop_loss_percentage",
            "is_active",
        )