from datetime import datetime, timedelta

from core.choice_field_types import StatusChoice
from signals.models import TradingSignal
from core.api_gateways import ConfigServerClient
from core.celery import app
from signals.utils import market_fetcher


@app.task(name="delete_not_started_signals")
def delete_not_started_signals():
    day_limit = int(ConfigServerClient.get_application_settings()[
                        "remove_pending_signals_days"
                    ])
    TradingSignal.objects.filter(
        created_at__lte=datetime.now() - timedelta(days=day_limit),
        start_datetime__isnull=True,
        entry_point_hit_datetime__isnull=True
    ).update(is_deleted=True, state=StatusChoice.DELETED)


@app.task(name="fetch_update_markets")
def fetch_update_markets():
    # Fetches And updates All markets (bingx,bybit for now)
    market_fetcher()