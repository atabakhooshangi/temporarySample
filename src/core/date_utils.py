from typing import List, Tuple
from datetime import date, timedelta


def previous_week_range(date: date) -> Tuple[date, date]:
    """
    returns the start date and end date of the previous week
    """
    start_date = date + timedelta(-date.weekday(), weeks=-1)
    end_date = date + timedelta(-date.weekday() - 1)
    return start_date, end_date


def previous_month_range(date: date) -> Tuple[date, date]:
    """
    returns the start date and end date of the previous month
    """
    month_start = date.replace(day=1)
    previous_month_end = month_start - timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1)
    return previous_month_start, previous_month_end


def days_between_dates(start_date: date, end_date: date) -> List[date]:
    """
    return the list of dates between two date
    """
    return [
        start_date + timedelta(days=day) for day in range(
            (end_date - start_date).days + 1
        )
    ]
