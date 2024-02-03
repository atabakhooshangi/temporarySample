from rest_framework import response
from rest_framework.pagination import PageNumberPagination, CursorPagination, BasePagination
from rest_framework.utils.urls import replace_query_param

from core.settings import PAGE_SIZE
from signals.models import TradingSignal

from base64 import b64encode
from urllib import parse


class CustomPaginator(PageNumberPagination):
    """Custom pagination """

    def paginate_queryset(self, queryset, request, view=None):
        """ determine the number of records should be shown dynamically. base on page_size parameter"""
        self.page_size = request.query_params.get('page_size') if request.query_params.get(
            'page_size') else PAGE_SIZE
        return super().paginate_queryset(queryset, request)

    def get_paginated_response(self, data):
        return response.Response({
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'count': self.page.paginator.count,
            'last_page': self.page.paginator.page_range.stop - 1,
            'page_size': self.page_size,
            'current_page_no': self.page.number,
            'results': data,
        })


class CustomCursorPaginator(CursorPagination):
    """Custom pagination """

    def set_ordering_param(self, request):
        ordering_param_list = request.query_params.get('ordering', '-created_at')
        self.ordering = ordering_param_list.split(',')

    def paginate_queryset(self, queryset, request, view=None):
        """ determine the number of records should be shown dynamically. base on page_size parameter"""
        self.page_size = int(request.query_params.get('page_size'))if request.query_params.get(
            'page_size') else PAGE_SIZE
        self.set_ordering_param(request)
        return super().paginate_queryset(queryset, request)

    def encode_cursor(self, cursor):
        """
        Given a Cursor instance, return an url with encoded cursor.
        """
        tokens = {}
        if cursor.offset != 0:
            tokens['o'] = str(cursor.offset)
        if cursor.reverse:
            tokens['r'] = '1'
        if cursor.position is not None:
            tokens['p'] = cursor.position

        querystring = parse.urlencode(tokens, doseq=True)
        encoded = b64encode(querystring.encode('ascii')).decode('ascii')
        return encoded, replace_query_param(self.base_url, self.cursor_query_param, encoded)

    def get_paginated_response(self, data):
        get_next_link = self.get_next_link()
        get_previous_link = self.get_previous_link()
        next_fingerprint, next_link = get_next_link if get_next_link else (None, None)
        previous_fingerprint, previous_link = get_previous_link if get_previous_link else (None, None)

        return response.Response({
            'next': next_link,
            'next_fingerprint': next_fingerprint,
            'previous': previous_link,
            'previous_fingerprint': previous_fingerprint,
            'page_size': self.page_size,
            'results': data,
        })


class ServiceSignalsPaginator(CustomPaginator):
    def get_paginated_response(self, data):
        return response.Response({
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'count': self.page.paginator.count,
            'last_page': self.page.paginator.page_range.stop - 1,
            'page_size': self.page_size,
            'current_page_no': self.page.number,
            'vip_signal': TradingSignal.objects.filter(sid=self.request.query_params.get('pk')).count,
            'results': data,
        })


class MultiplePaginationMixin:
    CURSOR = 'cursor'
    PAGE_NUM = 'page_number'

    def __new__(self, request):
        _pagination_type = request.query_params.get('pagination_type')
        if _pagination_type == self.CURSOR:
            return CustomCursorPaginator()
        return CustomPaginator()

