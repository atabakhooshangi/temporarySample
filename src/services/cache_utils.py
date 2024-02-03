import json
from datetime import date

from django.core.serializers.json import DjangoJSONEncoder
from django_redis import get_redis_connection

from services.models import DailyROI, DailyAggregatedPnl
from services.utils import calculate_maximum_draw_down, calculate_initial_draw_down


def cache_roi_and_draw_down(service, expire_in: int, history_type, include_current_day=False):
    """
    cache the roi and draw down for this service in caching db(redis here)
    draw down is recalculated but the roi is only queried from db.
    """
    with get_redis_connection(alias="data_cache") as redis_conn:
        roi_list = list(
            DailyROI.objects.filter(
                roi_history__history_type=history_type,
                roi_history__service=service
            ).order_by("number").values("date", "percentage","amount")
        )
        if include_current_day:
            today = date.today()
            today_roi = DailyAggregatedPnl.objects.filter(
                date=today,
                service_id=service.id,
            )

            if today_roi.exists():
                today_roi = today_roi.first()
                # combine the values in the final result
                roi_list = roi_list + [
                    dict(
                        date=today,
                        percentage=roi_list[-1]["percentage"] + today_roi.percentage,
                        amount=roi_list[-1]["amount"] + today_roi.amount

                    )
                ]
        roi_percentages = [roi["percentage"] for roi in roi_list]
        draw_down = calculate_maximum_draw_down(roi_percentages)
        initial_draw_down = calculate_initial_draw_down(roi_percentages)
        data = dict(
            roi_list=roi_list,
            draw_down=draw_down,
            initial_draw_down=initial_draw_down,
        )
        redis_conn.set(
            f"{history_type.upper()}:service_id:{service.id}",
            json.dumps(data, cls=DjangoJSONEncoder),
            expire_in
        )
        return data
