from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)

@dataclass
class TradeOrder:
    symbol: str
    lot_size: float
    order_type: str  # 'buy' or 'sell'
    price: float
    stop_loss: float
    take_profit: float
    magic_number: int
    comment: str = ""

@dataclass
class TradeResult:
    success: bool
    order_id: Optional[int]
    price: float
    error_description: str = ""

class ExecutionEngine:
    """
    Handles execution of trade orders using MetaTrader 5.
    """
    def __init__(self, magic_number: int):
        self.magic_number = magic_number
        self.logger = logging.getLogger(__name__)
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize connection to MT5."""
        if not mt5.initialize():
            self.logger.error(f"ExecutionEngine: mt5.initialize() failed, error code: {mt5.last_error()}")
            return False
        self._initialized = True
        return True

    def shutdown(self):
        """Shutdown MT5 connection."""
        if self._initialized:
            mt5.shutdown()
            self._initialized = False

    def place_market_order(self, order: TradeOrder) -> TradeResult:
        """
        Place a market order.
        """
        if not self._initialized:
            return TradeResult(False, None, 0.0, "Execution engine not initialized")

        symbol_info = mt5.symbol_info(order.symbol)
        if symbol_info is None:
            return TradeResult(False, None, 0.0, f"Symbol {order.symbol} not found")

        if not symbol_info.visible:
            if not mt5.symbol_select(order.symbol, True):
                return TradeResult(False, None, 0.0, f"Failed to select symbol {order.symbol}")

        action = mt5.TRADE_ACTION_DEAL
        if order.order_type.lower() == 'buy':
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(order.symbol).ask
        elif order.order_type.lower() == 'sell':
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(order.symbol).bid
        else:
            return TradeResult(False, None, 0.0, f"Invalid order type: {order.order_type}")

        request = {
            "action": action,
            "symbol": order.symbol,
            "volume": float(order.lot_size),
            "type": order_type,
            "price": price,
            "sl": float(order.stop_loss),
            "tp": float(order.take_profit),
            "deviation": 20,
            "magic": self.magic_number,
            "comment": order.comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Attempt to send order
        result = mt5.order_send(request)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            error_msg = f"Order failed: {result.retcode} {result.comment}"
            self.logger.error(error_msg)
            return TradeResult(False, None, 0.0, error_msg)

        self.logger.info(f"Order placed successfully: ticket={result.order}, price={result.price}")
        return TradeResult(True, result.order, result.price)