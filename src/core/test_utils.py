from unittest.mock import patch

from rest_framework.test import APITestCase
from celery import current_app

from django.test.runner import DiscoverRunner
from django.conf import settings

from user.models.users import IAMUser


TEST_USER = IAMUser(owner_id=1, authentication_level=None, is_authenticated=True)


def force_authenticator(method):
    """
    this decorator can be used on a test function/method to authenticate it
    with the predefined test users
    """
    def wrapper(instance: APITestCase, *args, **kwargs):
        instance.client.force_authenticate(user=TEST_USER)
        method(instance, *args, **kwargs)

    return wrapper


def arbitrary_user_force_authenticator(user: IAMUser, *args, **kwargs):
    """
    this decorator can be used on a test function/method to authenticate it
    with the passed user object
    """
    def decorator(method):
        def wrapper(instance: APITestCase, *args, **kwargs):
            instance.client.force_authenticate(user=user)
            method(instance, *args, **kwargs)
        return wrapper

    return decorator


def patched_application_settings():
    return {
            "settlement_affirmation_days": 0,
            "remove_pending_signals_days": 1,
            "social_ranking_page_signals_limit": 1
        }



class TestRunner(DiscoverRunner):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def __disable_celery():
        """
        disables the celery in the test envrionment
        """
        settings.CELERY_BROKER_URL = current_app.conf.CELERY_BROKER_URL = f'filesystem:///dev/null/'
        settings.BROKER_TRANSPORT_OPTIONS = current_app.conf.BROKER_TRANSPORT_OPTIONS = {
            'data_folder_in': '/tmp',
            'data_folder_out': '/tmp',
            'data_folder_processed': '/tmp',
        }

    def setup_test_environment(
        self,
        **kwargs
    ):
        TestRunner.__disable_celery()
        super(TestRunner, self).setup_test_environment(**kwargs)