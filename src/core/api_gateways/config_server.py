import json
from collections import OrderedDict

import requests

from django.conf import settings
from django_redis import get_redis_connection


class ConfigServerClient:

    class ConfigServerClientException(Exception):
        pass

    @staticmethod
    def mock_json():
        return dict(
                    trial_limitation=10,
                    settlement_affirmation_days=0,
                    remove_pending_signals_days=1,
                    social_ranking_page_signals_limit=1,
                )

    @classmethod
    def get_application_settings(cls):

        # MOCK IF IN UNITTESTS
        try:

            # MOCK IF IN UNITTESTS
            if settings.TESTING:
                response = OrderedDict()
                setattr(response, 'text', cls.mock_json())
                setattr(response, 'status_code', 200)
                setattr(response, 'json', cls.mock_json)
                with get_redis_connection('data_cache') as redis_conn:
                        redis_conn.set(
                            settings.CONSOLE_SETTINGS_REDIS_KEY,
                            json.dumps(response.json())
                        )
            else:
                response = requests.get(
                    url=f"{settings.CONFIG_SERVER_BASE_URL}application/settings?raw=true",
                )
        except Exception as exc:
            print("Could not fetch data from consul(Application settings)")
            print(exc.args)
            raise exc

        if response.status_code == 200:

            return response.json()
        else:
            raise cls.ConfigServerClientException
