from django.db.models import F, Window, OuterRef
from django.db.models.functions import Rank
from rest_framework.filters import OrderingFilter

from core.sql_functions import SubqueryCount
from signals.models import VendorFollower


class ServiceOrderingFilter(OrderingFilter):

    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)
        if ordering:
            f_ordering = []
            for o in ordering:
                if o[0] == '-':
                    f_ordering.append(F(o[1:]).desc(nulls_last=True))
                else:
                    f_ordering.append(F(o).asc(nulls_last=True))

        if ordering and ('popularity' in ordering or '-popularity' in ordering):
            queryset = queryset.annotate(
                popularity=SubqueryCount(
                    VendorFollower.objects.filter(
                        vendor__services__id=OuterRef("pk"),
                    )
                )  # Count("profile__vendor_follower")
            ).order_by(*f_ordering)
        if ordering and ('win_rate' in ordering or '-win_rate' in ordering):
            return queryset.order_by(*f_ordering)
        if ordering and ('cost_and_benefit' in ordering or '-cost_and_benefit' in ordering):
            queryset = queryset.order_by(*f_ordering)
            return queryset
        return super().filter_queryset(request, queryset, view)


class ServiceRankingOrdering(OrderingFilter):
    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)

        if ordering and ('total_roi' in ordering or '-total_roi' in ordering):
            queryset = queryset.annotate(row_number=Window(
                expression=Rank(),
                order_by=F('total_roi').desc()
            )
            ).order_by('-total_roi')
        return queryset
