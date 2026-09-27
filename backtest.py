import sys
# We mock MetaTrader5 BEFORE importing bot
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
            time = int(datetime.now().timestamp())
            volume = 100
        return Tick()

    def order_send(self, request):
        class OrderResult:
            retcode = MockMT5.TRADE_RETCODE_DONE
            comment = "Mock order placed"
            order = 12345
            price = request.get('price', 1.0)
        return OrderResult()

sys.modules['MetaTrader5'] = MockMT5()

import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Dict, Optional

# Now we can safely import other modules that might use MT5
from bot import TradingBot
from execution_engine import ExecutionEngine, TradeOrder, TradeResult
from data_engine import Bar

class MockExecutionEngine(ExecutionEngine):
    """
    Simulates order execution without connecting to a real broker.
    """
    def __init__(self, magic_number: int):
        super().__init__(magic_number)
        self.order_counter = 0

    def initialize(self) -> bool:
        self._initialized = True
        return True

    def shutdown(self):
        self._initialized = False

    def place_market_order(self, order: TradeOrder) -> TradeResult:
        if not self._initialized:
            return TradeResult(False, None, 0.0, "Execution engine not initialized")

        self.order_counter += 1
        self.logger.info(f"BACKTEST: Mock placing order for {order.symbol} at {order.price}")
        return TradeResult(True, self.order_counter, order.price)

class BacktestBot(TradingBot):
    """
    Extends TradingBot to run over historical data instead of live ticks.
    """
    def __init__(self, config_path: str = "config.yaml"):
        super().__init__(config_path)
        # Override execution engine with mock
        self.execution_engine = MockExecutionEngine(magic_number=self.config['execution']['magic_number'])
        self.execution_engine.initialize()

        # Backtest state
        self.initial_balance = self.config.get('initial_balance', 10000.0)
        self.account_balance = self.initial_balance
        self.account_equity = self.initial_balance

    def _get_latest_tick(self, symbol: str) -> Optional[Dict]:
        """Override to prevent querying MT5 in backtest"""
        return None

    def _update_equity_from_positions(self, current_price: float):
        """Update P&L simulation."""
        total_pnl = 0.0
        # Contract size default to 100,000
        contract_size = 100000.0

        for ticket, position in self.open_positions.items():
            if position['signal'] == 'BUY':
                # Simplified PnL
                pnl = (current_price - position['entry_price']) * position['lot_size'] * contract_size
            else:
                pnl = (position['entry_price'] - current_price) * position['lot_size'] * contract_size
            total_pnl += pnl

        self.account_equity = self.account_balance + total_pnl

    def run_backtest(self, historical_data: Dict[str, pd.DataFrame]):
        """
        Run backtest by feeding OHLCV bars directly.
        historical_data: dict of symbol -> DataFrame with columns ['time', 'open', 'high', 'low', 'close', 'volume']
        """
        logger.info("Starting backtest...")

        # Override _process_symbol to simulate execution better, we'll patch it locally for backtest

        for symbol, df in historical_data.items():
            if symbol not in self.symbols:
                continue

            logger.info(f"Processing historical data for {symbol} ({len(df)} bars)")
            for _, row in df.iterrows():

                bar = Bar(
                    time=row['time'],
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row['volume'],
                    symbol=symbol
                )

                # Update PnL before processing the bar
                self._update_equity_from_positions(bar.close)

                # Update tracking for the monitor
                self.monitor.update_equity(bar.time, self.account_equity)

                self._update_bar_history(symbol, bar)

                # Check for SL / TP
                positions_to_close = []
                for ticket, pos in list(self.open_positions.items()):
                    if pos['signal'] == 'BUY':
                        if bar.low <= pos['initial_sl'] or bar.high >= pos['initial_tp']:
                            positions_to_close.append((ticket, bar.close))
                    else:
                        if bar.high >= pos['initial_sl'] or bar.low <= pos['initial_tp']:
                            positions_to_close.append((ticket, bar.close))

                for ticket, price in positions_to_close:
                    pos = self.open_positions.pop(ticket)
                    if pos['signal'] == 'BUY':
                        pnl = (price - pos['entry_price']) * pos['lot_size'] * 100000.0
                    else:
                        pnl = (pos['entry_price'] - price) * pos['lot_size'] * 100000.0

                    self.account_balance += pnl
                    self.account_equity = self.account_balance
                    logger.info(f"BACKTEST: Position {ticket} closed. PnL: {pnl:.2f}. Balance: {self.account_balance:.2f}")

                # Process new signals
                # Monkey patch entry price for backtest so it uses bar close

                self._generate_and_process_signal(symbol, bar.time)

        self.monitor.save_equity_curve("backtest_equity_curve.png")
        logger.info(f"Backtest completed. Final Equity: {self.account_equity:.2f}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("backtest")

    # Generate some dummy historical data for testing
    now = datetime.now()
    dates = [now - timedelta(minutes=i) for i in range(100, 0, -1)]

    # Create an uptrend to trigger SMA crossovers
    close_prices = [1.0000 + (i * 0.0001) for i in range(100)]

    dummy_data = {
        "EURUSD": pd.DataFrame({
            "time": dates,
            "open": close_prices,
            "high": [c + 0.0001 for c in close_prices],
            "low": [c - 0.0001 for c in close_prices],
            "close": close_prices,
            "volume": [100] * 100
        })
    }

    bot = BacktestBot()
    bot.run_backtest(dummy_data)
