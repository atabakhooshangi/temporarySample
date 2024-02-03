from django.db.models import Func, PositiveIntegerField, Subquery, DecimalField


# functions mostly copy pasted from the www so skip the details :)

class PostgresExtractMinute(Func):
    """
    custom postgres function that extract minute values from
    epoch timestamp
    """
    function = "EXTRACT"
    template = "%(function)s(epoch FROM %(expressions)s) / 60"

class PostgresExtractDate(Func):
    """
    custom postgres function that extract date values from
    epoch timestamp
    """
    function = "EXTRACT"
    template = "%(function)s(epoch FROM %(expressions)s) / 86400"

class PostgresRound(Func):
    # round the aggregated expression to two decimal places
    function = "ROUND"
    template = "%(function)s(%(expressions)s::numeric, 2)"


class SubqueryAggregate(Subquery):
    # https://code.djangoproject.com/ticket/10060
    template = '(SELECT %(function)s(_agg."%(column)s") FROM (%(subquery)s) _agg)'

    def __init__(self, queryset, column, output_field=None, **extra):
        if not output_field:
            # infer output_field from field type
            output_field = queryset.model._meta.get_field(column)
        super().__init__(queryset, output_field, column=column, function=self.function, **extra)


class SubquerySum(SubqueryAggregate):
    """
    calculate summation of a field on a subquery
    usage: SubquerySum(queryset, "field1")
    """
    function = 'SUM'


class SubqueryAvg(SubqueryAggregate):
    """
    calculate Average of a field on a subquery
    usage: SubqueryAvg(queryset, "field1")
    """
    function = 'AVG'


class SubqueryCount(Subquery):
    """
    find the count of the subquery result
    usage: SubqueryCount(queryset)
    """
    template = "(SELECT COUNT(*) FROM (%(subquery)s) _count)"
    output_field = PositiveIntegerField()


class RoundWithPlaces(Func):
    function = 'ROUND'
    template = "%(function)s(%(expressions)s::numeric, 2)"

