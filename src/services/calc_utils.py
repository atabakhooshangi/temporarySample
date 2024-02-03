from services.tasks import (
    calculate_roi_and_draw_down,
    calculate_pnl,
    calculate_daily_aggregated_pnl_for_all_dates,
    calculate_today_daily_aggregated_pnl, frozen_balance_correction, total_balance_correction
)


def calc_pnl(services_id_list):
    calculate_pnl.delay(services_id_list)
    return True


def calc_roi(services_id_list):
    calculate_roi_and_draw_down.delay(services_id_list)
    return True


def calc_today_aggregated_pnl(services_id_list):
    calculate_today_daily_aggregated_pnl.delay(services_id_list)
    return True


def calc_aggregated_pnl(services_id_list):
    calculate_daily_aggregated_pnl_for_all_dates.delay(services_id_list)
    return True


def correct_frozen_balances(services_id_list):
    frozen_balance_correction.delay(services_id_list)
    return True

def correct_total_balances(services_id_list):
    total_balance_correction.delay(services_id_list)
    return True