from copytrading.exceptions import CCXTExceptionCreateOrderAmountValue


class ExchangeMessageText:
    exception_message = {
        'bybit amount of coin_name must be greater than minimum amount precision of 0.001': CCXTExceptionCreateOrderAmountValue
    }
