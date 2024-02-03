import json
import logging
import re
from datetime import datetime
from typing import Union

from django.utils.translation import gettext as _
from rest_framework import status

from core.base_exception import BaseApiException
from core.message_text import MessageText

logger = logging.getLogger(__name__)


class JsonParser:
    def parse(self, json_string):
        return json.loads(json_string)


class CodedExceptionMapper:
    def __init__(self):
        self.exceptions = {
            101204: InsufficientMarginException,
            101400: BingxInvalidTPException,
        }

    def get_exception(self, code):
        return self.exceptions.get(code, None)


class PatternedExceptionMapper:
    def __init__(self):
        self.exceptions = {
            r'amount of .* must be greater than minimum amount precision of \d+': BingxInvalidPrecisionException,
        }

    def find_pattern(self, msg):
        for pattern, exception in self.exceptions.items():
            if re.search(pattern, msg):
                return self.exceptions[pattern]
        return None


class BingXErrorMsg:
    BingXNotHaveSymbolKey = "bingx does not have market symbol"
    TakeProfitMustBeHigher = "TakeProfitPrice must be higher than entrustPrice"
    TakeProfitMustBeLower = "TakeProfitPrice must be lower than entrustPrice"
    StopLossMustBeLower = "StopLossPrice price must lower than fair price"
    StopLossMustBeGreater = "StopLossPrice price must greater than fair price"
    LeverageIsNotValid = ("Invalid parameters, err:Key: 'APISetLeverageRequest.Leverage' "
                          "Error:Field validation for 'Leverage' failed on the 'required' tag")
    CheckLimitPriceMinPrice = "checkPriceLimit entrustPrice must greater than minPrice"
    CheckLimitPriceMaxPrice = "checkPriceLimit entrustPrice must less than maxPrice"
    OrderAlreadyFilled = "order is already filled"

    STATIC_ERRORS = {
        TakeProfitMustBeHigher: [MessageText.TakeProfitMustBeHigher, True],
        TakeProfitMustBeLower: [MessageText.TakeProfitMustBeLower, True],
        StopLossMustBeLower: [MessageText.StopLossMustBeLower, True],
        StopLossMustBeGreater: [MessageText.StopLossMustBeGreater, True],
        BingXNotHaveSymbolKey: [MessageText.BingXNotHaveSymbol, True],
        LeverageIsNotValid: [MessageText.BingXLeverageIsInvalid, True],
        CheckLimitPriceMinPrice: [MessageText.CheckLimitPriceMinPrice, True],
        CheckLimitPriceMaxPrice: [MessageText.CheckLimitPriceMaxPrice, True],
        OrderAlreadyFilled: [MessageText.OrderAlreadyFilled, True],
    }

    def __init__(self):
        self.json_parser = JsonParser()
        self.coded_exception_mapper = CodedExceptionMapper()
        self.patterned_exception_mapper = PatternedExceptionMapper()

    def parse_json_garbage(self, s) -> (bool, Union[dict, str]):  # returns status and parsed json or string
        try:
            s = s[next(idx for idx, c in enumerate(s) if c in "{["):]
            return True, json.loads(s)
        except json.JSONDecodeError as e:
            try:
                return True, json.loads(s[:e.pos])
            except json.JSONDecodeError:
                return False, s
            except StopIteration:
                return False, s

    def detect_static_errors(self, message: str, price=None, take_profit=None, stop_loss=None):
        data = self.STATIC_ERRORS.get(message, [message, True])
        if self.BingXNotHaveSymbolKey in message:
            symbol = message.replace(self.BingXNotHaveSymbolKey + " ", "")
            data = [
                MessageText.BingXNotHaveSymbol % symbol,
                True
            ]
        if message in [
            self.TakeProfitMustBeHigher,
            self.TakeProfitMustBeLower,
        ]:
            data = [
                data[0] % (take_profit, price),
                True
            ]
        elif message in [
            self.StopLossMustBeLower,
            self.StopLossMustBeGreater,
            ]:
            data = [
                data[0] % (stop_loss, price),
                True
            ]
        error = ""
        is_error = True
        if data:
            error = data[0]
            is_error = data[1]
        return error, is_error

    def fetch_msg(self, original_msg: str):
        json_part = original_msg.split(" ", 1)[1]
        try:
            error_data = self.json_parser.parse(json_part)
            msg_code = error_data.get("code")
            msg_value = error_data.get("msg", json_part)
        except Exception as e:
            msg_value = json_part
            msg_code = None
        print(msg_value, msg_code)
        return msg_value, msg_code

    def handle_error(self, original_msg: str, price=None, take_profit=None, stop_loss=None):
        parsed, result = self.parse_json_garbage(original_msg)
        print("result", result)
        is_error = True
        if not parsed:
            return original_msg, {}, is_error
        if result.get('code') == 101204:
            return MessageText.InsufficientMargin400, {}, is_error
        error, is_error = self.detect_static_errors(result.get('msg'), price, take_profit, stop_loss)
        if error:
            return error, {}, is_error
        return original_msg, {}, is_error
        # msg, code = self.fetch_msg(original_msg)
        # coded_exception_class = self.coded_exception_mapper.get_exception(code)
        # if coded_exception_class:
        #     return coded_exception_class
        # patterned_exception_class = self.patterned_exception_mapper.find_pattern(msg)
        # if patterned_exception_class:
        #     return patterned_exception_class
        # return CCXTException(detail=msg)


class ByBitErrorMsg:
    # NOTE: static errors: object of [error_message, is_error?], is_error indicates if this is an error or not
    PriceIsInvalidKey = "price is invalid"
    ByBitNotHaveSymbolKey = "bybit does not have market symbol"
    LeverageNotModifiedKey = "leverage not modified"
    OrderNotModifiedKey = "order not modified"
    BuyLeverageNotValid = "buy leverage invalid"
    STATIC_ERRORS = {
        PriceIsInvalidKey: [MessageText.PriceIsInvalid400, True],
        ByBitNotHaveSymbolKey: [MessageText.ByBitNotHaveSymbol, True],
        LeverageNotModifiedKey: ["leverage not modified", False],
        OrderNotModifiedKey: ["order not modified", False],
        BuyLeverageNotValid: [MessageText.InvalidLeverage, True],
    }
    word_mapper = {
        "tp": "Take profit",
        "sl": "Stop loss"
    }

    def replace_numbers(self, match):
        matched_number = match.group()
        new_number = str(int(matched_number) / 10 ** 8)
        return new_number

    def parse_json_garbage(self, s) -> (bool, Union[dict, str]):  # returns status and parsed json or string
        try:
            s = s[next(idx for idx, c in enumerate(s) if c in "{["):]
            return True, json.loads(s)
        except json.JSONDecodeError as e:
            try:
                return True, json.loads(s[:e.pos])
            except json.JSONDecodeError:
                return False, s
        except StopIteration:
            return False, s

    def detect_tp_sl_less_than_10_pcnt(self, text, price=None, take_profit=None, stop_loss=None):
        pattern = r'(sl|tp)\(0\):(\d+) < \d+_pcnt of base:(\d+)'
        match = re.search(pattern, text.encode('utf-8').decode('unicode_escape'))
        if match:
            position_side, sl_or_tp_number, base_price = match.groups()
            float_points = len(f"{base_price}") - len(f"{int(price)}")
            base_price = int(base_price) / 10 ** float_points
            readable_error_message = (f"{self.word_mapper.get(position_side)}: "
                                      f"should be greater than 10 percent of entry point")
            data = {
                "position_side": self.word_mapper.get(position_side),
                "sl_or_tp_number": int(sl_or_tp_number) / 10 ** float_points,
                "base_price": base_price * 0.1
            }
            if data.get("position_side") == "Stop loss":
                readable_error_message = (MessageText.StopLossLessThanTenPercent % stop_loss)
            if data.get("position_side") == "Take profit":
                readable_error_message = (MessageText.TakeProfitLessThanTenPercent % take_profit)
            return readable_error_message, data
        else:
            return None, None

    def detect_sl_or_tp_too_high(self, text, price=None, take_profit=None, stop_loss=None):
        pattern = r'(sl|tp)\(0\):(\d+) too high'
        match = re.search(pattern, text)
        if match:
            position_side, sl_or_tp_number = match.groups()
            readable_error_message = f"{self.word_mapper.get(position_side)}: (%s) is too high"
            data = {
                "position_side": self.word_mapper.get(position_side),
                "sl_or_tp_number": int(sl_or_tp_number) / 10 ** 4 #10 ** (len(f"{sl_or_tp_number}") - len(f"{int(price)}"))
                # sl_or_tp_number
            }
            if data.get("position_side") == "Stop loss":
                readable_error_message = MessageText.StopLossIsTooHigh400 % stop_loss
            if data.get("position_side") == "Take profit":
                readable_error_message = MessageText.TakeProfitIsTooHigh400 % take_profit
            return readable_error_message, data
        else:
            return None, None

    def extract_tp_sl_errors(self, text, price=None):
        pattern = (r'(tp|sl):(\d+) set for (\w+) position should '
                   r'(greater|lower than|be lower than|be higher than) base_price:(\d+)')
        match = re.search(pattern, text)

        if match:
            position_side, sl_or_tp_number, position_word, comparison_phrase, base_price_number = match.groups()
            float_points = len(f"{base_price_number}") - len(f"{int(price)}")
            data = {
                "position_side": self.word_mapper.get(position_side),
                "sl_or_tp_number": int(sl_or_tp_number) / 10 ** float_points,
                "position_word": position_word,
                "comparison_phrase": comparison_phrase.replace('be ', ''),
                "base_price_number": int(base_price_number) / 10 ** float_points
            }
            readable_error_message = (f"{data.get('position_side')} (%s) for {position_word} position should be "
                                      f"{data.get('comparison_phrase')} (%s)")
            if "Take profit" == data.get("position_side"):
                if data.get("position_word") == "Buy" and "higher" in data.get("comparison_phrase"):
                    readable_error_message = (MessageText.TakeProfitBuyShouldBeGreaterThan %
                                              (data.get('sl_or_tp_number'), data.get('base_price_number')))
                else:
                    readable_error_message = (MessageText.TakeProfitSellShouldBeLowerThan %
                                              (data.get('sl_or_tp_number'), data.get('base_price_number')))
            if "Stop loss" == data.get("position_side"):
                if data.get("position_word") == "Buy" and "lower" in data.get("comparison_phrase"):
                    readable_error_message = (MessageText.StopLossBuyShouldBeLowerThan %
                                              (data.get('sl_or_tp_number'), data.get('base_price_number')))
                else:
                    readable_error_message = (MessageText.StopLossSellShouldBeGreaterThan %
                                              (data.get('sl_or_tp_number'), data.get('base_price_number')))

            return readable_error_message, data
        else:
            return None, None

    def detect_static_errors(self, message: str):
        data = self.STATIC_ERRORS.get(message, [message, True])
        if self.ByBitNotHaveSymbolKey in message:
            symbol = message.replace(self.ByBitNotHaveSymbolKey + " ", "")
            data = [
                MessageText.ByBitNotHaveSymbol % symbol,
                True
            ]
        error = ""
        is_error = True
        if data:
            error = data[0]
            is_error = data[1]
        return error, is_error

    def fetch_bybit_exception(self, message: str, price=None, take_profit=None, stop_loss=None,  symbol: str = None):
        parsed, result = self.parse_json_garbage(message)
        is_error = True
        if not parsed:
            error, is_error = self.detect_static_errors(message)
            if error:
                return error, {}, is_error
            return message, {}, is_error
        msg, data = self.extract_tp_sl_errors(result.get('retMsg'), price)
        if msg:
            return msg, data, is_error
        msg, data = self.detect_sl_or_tp_too_high(result.get('retMsg'), price, take_profit, stop_loss)
        if msg:
            return msg, data, is_error
        msg, data = self.detect_tp_sl_less_than_10_pcnt(result.get('retMsg'), price, take_profit, stop_loss)
        if msg:
            return msg, data, is_error
        # TODO: handle other errors if happened
        error, is_error = self.detect_static_errors(result.get('retMsg'))
        return error, {}, is_error


class FetchCCXTTextException:
    EXCHANGE_140043 = 140043
    EXCHANGE_10001 = 10001
    EXCHANGE_140003 = 140003
    EXCHANGE_110043 = 110043

    def fetch_exception(self, message: str, symbol: str = None):
        if 'retMsg' in message:
            start_index = message.find('{')
            end_index = message.rfind('}') + 1
            dict_str = message[start_index:end_index]
        else:
            if symbol in message:
                message = message.replace(symbol, 'coin_name')
            return message  # TODO: hande the translation of this exception message type.(like for ada put order with 23456 )
        try:
            result = json.loads(dict_str).get('retMsg')
            result = result.encode('utf-8').decode('unicode_escape')
            number_pattern = r'\d+'
            tp_pattern = r'tp\(0\.0\)'
            sl_pattern = r'sl\(0\.0\)'
            new_str = re.sub(number_pattern, self.replace_numbers, result)
            new_str = re.sub(tp_pattern, 'take profit', new_str)
            new_str = re.sub(sl_pattern, 'stop loss', new_str)
        except Exception as e:
            logger.exception(
                '{} :: {} Exception occurred while attempting to convert the exception message to JSON.'.format(
                    e,
                    datetime.now()))
            return dict_str
        return new_str

    def fetch_exception_code(self, message: str):
        if 'retCode' in message:
            start_index = message.find('{')
            end_index = message.rfind('}') + 1
            dict_str = message[start_index:end_index]
        else:
            return None
        try:
            result = json.loads(dict_str).get('retCode')
        except Exception as e:
            return None
            # raise e
        return result


# Bingx Errors
class BingxInvalidTPException(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.BingxInvalidTP400
    default_code = 400


class BingxInvalidPrecisionException(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.BingxInvalidPrecision400
    default_code = 400


class InsufficientMarginException(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.InsufficientMargin400
    default_code = 400


class InsufficientFundsException(BaseApiException):
    status_code = status.HTTP_406_NOT_ACCEPTABLE
    default_detail = MessageText.InsufficientFunds406
    default_code = 406


class ExchangeErrorException(BaseApiException):
    status_code = status.HTTP_406_NOT_ACCEPTABLE
    default_detail = MessageText.ExchangeError406
    default_code = 406


class NetworkErrorException(BaseApiException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = MessageText.NetworkError500
    default_code = 500


class ExchangeAuthenticationError(BaseApiException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = MessageText.AuthenticationError500
    default_code = 500


class CCXTException(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'An error occurred while interacting with the Exchange.'
    default_code = 400


class CCXTExceptionSetLeverage10001(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.InvalidLeverage
    default_code = 400


class CCXTExceptionCreateOrder10001(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.InvalidStopLosValue
    default_code = 400


class CCXTExceptionCreateOrder140003(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.ImpermissibleOrderPrice
    default_code = 400


class CCXTExceptionCreateOrderAmountValue(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.AmountValueNotAcceptable
    default_code = 400


class CCXTExceptionExceedsMaximumLimited(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "The number of contracts exceeds maximum limit allowed: too large"
    default_code = 400


class CCXTExceptionByBitNotHaveSymbol(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.ByBitNotHaveSymbol
    default_code = 400


class OrderNotFoundException(BaseApiException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = MessageText.OrderNotFound500
    default_code = 500


class ApiKeyNotSetException(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.ApiKeyNotSet400
    default_code = 400


class OrderISNotCancel(BaseApiException):
    status = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.ThisOrderIsNotCancel
    default_code = 400


class OrderISNotCloseable(BaseApiException):
    status = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.ThisOrderIsNotCloseable
    default_code = 400


class OrderIsNotEditable(BaseApiException):
    status = status.HTTP_400_BAD_REQUEST
    default_detail = MessageText.OrderIsNotEditable
    default_code = 400


class PositionHasBeenClosed(BaseApiException):
    status = status.HTTP_406_NOT_ACCEPTABLE
    default_detail = MessageText.PositionHasBeenClosed
    default_code = 404


class NoTradingHistoryFound(BaseApiException):
    status = status.HTTP_404_NOT_FOUND
    default_detail = MessageText.NoHistoryFound
    default_code = 404
