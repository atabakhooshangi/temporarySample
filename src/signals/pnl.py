import math

from core.choice_field_types import (
    TradingSignalType,
    PositionChoice,
)
from core.utils import convertor
from signals.models import TradingSignal

INITIAL_FUND = 1000


class SignalPnLCalculator:
    def __init__(self, signal: TradingSignal, quote_currency, base_currency):
        self.signal = signal
        self.quote_currency = quote_currency
        self.base_currency = base_currency
        self.entry_point = convertor(
            signal.entry_point,
            quote_currency,
            base_currency,
            'decimal'
        )
        self.take_profit_1 = convertor(
            signal.take_profit_1,
            quote_currency,
            base_currency,
            'decimal'
        )
        self.stop_los = convertor(
            signal.stop_los,
            quote_currency,
            base_currency,
            'decimal'
        )
        if signal.take_profit_2 is not None:
            self.take_profit_2 = convertor(
                signal.take_profit_2,
                quote_currency,
                base_currency,
                'decimal'
            )
        else:
            self.take_profit_2 = None
        self.manual_closure_price = signal.manual_closure_price
        if self.take_profit_2 is not None:
            self.tp1_volume = self.signal.volume / 100
            self.tp2_volume = 1 - self.tp1_volume
        else:
            self.tp1_volume = 1
            self.tp2_volume = 0

    def get_leverage(self):
        if self.signal.type == TradingSignalType.SPOT:
            leverage = 1
        elif self.signal.type == TradingSignalType.FUTURES:
            if self.signal.position == PositionChoice.LONG:
                leverage = self.signal.leverage
            elif self.signal.position == PositionChoice.SHORT:
                leverage = self.signal.leverage * -1
        return leverage

    def get_tp_profits(self):
        # if signal is closed with tp1 or tp2
        if self.signal.take_profit_1_hit_datetime is not None:
            # calculate the profit from tp1 if the signal hitted tp1
            tp1_profit = (
                                 self.take_profit_1 - self.entry_point
                         ) * self.tp1_volume / self.entry_point
            if (
                    self.take_profit_2 is not None
                    and
                    self.signal.take_profit_2_hit_datetime
            ):
                tp2_profit = (
                                     self.take_profit_2 - self.entry_point
                             ) * self.tp2_volume / self.entry_point
            else:
                tp2_profit = 0
        else:
            tp1_profit = 0
            tp2_profit = 0
        return tp1_profit, tp2_profit

    def get_sl_profit(self):
        if self.signal.stop_los_hit_datetime is not None:
            # calculate the loss from sl if the signal hitted sl
            if self.signal.take_profit_1_hit_datetime is not None:
                sl_loss = (
                                  self.stop_los - self.entry_point
                          ) * self.tp2_volume / self.entry_point
            else:
                sl_loss = (
                                  self.stop_los - self.entry_point
                          ) / self.entry_point
        else:
            sl_loss = 0
        return sl_loss

    def get_manual_closure_profit(self):
        if self.manual_closure_price is not None:
            # calculate the profit/loss from closing signal manually if it was
            # closed manually
            if (self.signal.take_profit_1_hit_datetime is not None):  # Position closed at second volume
                manual_closure_profit = (
                                                self.manual_closure_price - self.entry_point
                                        ) * self.tp2_volume / self.entry_point
            else:  # Position closed at 100%
                manual_closure_profit = (
                                                self.manual_closure_price - self.entry_point
                                        ) / self.entry_point
        else:
            manual_closure_profit = 0
        return manual_closure_profit

    def pnl_calculator(self):
        """
           this function will calculate the pnl percentage and amount
           for the passed signal based on the base and quote currency.
           some points about this function:
           - the signal must be closed
        """
        leverage = self.get_leverage()
        tp1_profit, tp2_profit = self.get_tp_profits()
        sl_loss = self.get_sl_profit()
        manual_closure_profit = self.get_manual_closure_profit()
        # aggregated and finalize the calculated variables
        total_profit_percentage = (
                                      (
                                              tp1_profit +
                                              tp2_profit +
                                              manual_closure_profit +
                                              sl_loss
                                      )
                                  ) * leverage
        total_profit_amount = total_profit_percentage * self.signal.virtual_value
        if self.signal.entry_point_hit_datetime is not None:
            return dict(
                pnl_amount=total_profit_amount,
                pnl_percentage=total_profit_percentage * 100,
            )
        else:
            return dict(
                pnl_amount=0,
                pnl_percentage=0
            )

    def possible_pnl_calculator(self):
        tp1_profit = (self.take_profit_1 - self.entry_point) * self.tp1_volume / self.entry_point
        if self.take_profit_2 is not None:
            tp2_profit = (self.take_profit_2 - self.entry_point) * self.tp2_volume / self.entry_point
        else:
            tp2_profit = 0

        sl_loss = (self.stop_los - self.entry_point) / self.entry_point
        max_total_profit_percentage = (
                                          (
                                                  tp1_profit +
                                                  tp2_profit
                                          )
                                      ) * self.get_leverage()
        min_total_profit_percentage = (
                                          (
                                              sl_loss
                                          )
                                      ) * self.get_leverage()
        self.signal.max_pnl_percentage = round(max_total_profit_percentage, 3)
        self.signal.min_pnl_percentage = round(min_total_profit_percentage, 3)
        self.signal.save()


def risk_evaluation(loss_percentage: float):
    """
    maps the loss percentage to a risk factor
    """
    if loss_percentage == math.inf:
        return 0
    elif 0 <= loss_percentage <= 2:
        return 1
    elif 2 < loss_percentage <= 5:
        return 2
    elif 5 < loss_percentage <= 10:
        return 3
    elif 10 < loss_percentage <= 17:
        return 4
    elif 17 < loss_percentage <= 27:
        return 5
    elif 27 < loss_percentage <= 40:
        return 6
    elif 40 < loss_percentage <= 60:
        return 7
    elif 60 < loss_percentage <= 90:
        return 8
    elif loss_percentage > 90:
        return 9
    else:
        raise ValueError("Invalid loss percentage")
