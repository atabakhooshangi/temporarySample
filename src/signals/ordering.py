from django.db import models
from rest_framework.filters import OrderingFilter

from core.choice_field_types import TradingOrderStatusChoices


class TradingOrderOrdering(OrderingFilter):
    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)
        if ordering and ('created_at' in ordering or '-created_at' in ordering):
            queryset = queryset.order_by(models.F('created_at').desc(nulls_last=True))
            return queryset
        if ordering and ('closed_at' in ordering or '-closed_at' in ordering):
            return queryset.order_by(models.F('closed_time').desc(nulls_last=True))
        return super().filter_queryset(request, queryset, view)


class PositionOrdering(OrderingFilter):
    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)
        if ordering:
            f_ordering = []
            for o in ordering:
                if o[0] == '-':
                    f_ordering.append(models.F(o[1:]).desc(nulls_last=True))
                else:
                    f_ordering.append(models.F(o).asc(nulls_last=True))

        if ordering and ('created_at' in ordering or '-created_at' in ordering):
            queryset = queryset.order_by(models.F('created_at').desc(nulls_last=True))
            return queryset
        if ordering and ('closed_at' in ordering or '-closed_at' in ordering):
            return queryset.order_by(models.F('closed_datetime').desc(nulls_last=True))
        return super().filter_queryset(request, queryset, view)
