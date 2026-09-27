class MockMT5:
    TRADE_RETCODE_DONE = 10009
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    TRADE_ACTION_DEAL = 1
    ORDER_TIME_GTC = 0
    ORDER_FILLING_IOC = 1

    def __init__(self):
        self._last_error = "No error"

    def initialize(self):
        return True

    def shutdown(self):
        pass

    def last_error(self):
        return self._last_error

    def account_info(self):
        class AccountInfo:
            equity = 10000.0
            balance = 10000.0
        return AccountInfo()

    def symbol_info(self, symbol):
        class SymbolInfo:
            visible = True
            trade_tick_value = 1.0
            trade_tick_size = 0.00001
            volume_min = 0.01
            volume_max = 100.0
            volume_step = 0.01
            trade_contract_size = 100000
        return SymbolInfo()

    def symbol_select(self, symbol, select):
        return True

    def symbol_info_tick(self, symbol):
        class Tick:
            bid = 1.0000
            ask = 1.0001
            time = 1600000000
            volume = 100
        return Tick()

    def order_send(self, request):
        class OrderResult:
            retcode = MockMT5.TRADE_RETCODE_DONE
            comment = "Mock order placed"
            order = 12345
            price = request.get('price', 1.0)
        return OrderResult()

import sys
sys.modules['MetaTrader5'] = MockMT5()
