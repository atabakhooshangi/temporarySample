import os

from celery import Celery
# set the default Django settings module for the 'celery' program.
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('config')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.beat_schedule = {
    "calculate_today_daily_aggregated_pnl": {
        "task": "calculate_today_daily_aggregated_pnl",
        "schedule": crontab(minute="*/30")
    },
    "calculate_pnl": {
        "task": "calculate_pnl",
        "schedule": crontab(minute="*/30")
    },
    "calculate_roi_and_draw_down": {
        "task": "calculate_roi_and_draw_down",
        "schedule": crontab(hour="1")  # run at morning(calculated roi for previous days)
    },
    "delete_not_started_signals": {
        "task": "delete_not_started_signals",
        "schedule": crontab(hour="1")  # run at morning(calculated roi for previous days)
    },
    "fetch_vendor_balance": {
        "task": "fetch_vendor_balance",
        "schedule": crontab(minute="*/30")
    },
    "fetch_console_setting": {
        "task": "fetch_console_setting",
        "schedule": crontab(minute="*/1")
    },
    "bybit_price_cacher": {
        "task": "bybit_price_cacher",
        "schedule": crontab(minute="*/5")
    },
    "civil_registry": {
        "task": "civil_registry",
        "schedule": crontab(hour="3")
    },
    "irt_price_updater": {
        "task": "irt_price_updater",
        "schedule": crontab(minute="*/5")
    }
}
# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
