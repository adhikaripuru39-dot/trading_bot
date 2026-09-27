from dataclasses import dataclass
from typing import Optional
import logging
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)

@dataclass
class TradeRisk:
    """Represents the risk parameters for a trade"""
    symbol: str
    signal: int  # 1 for BUY, -1 for SELL, 0 for NONE
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_amount: float  # Amount of money at risk in account currency
    risk_percent: float  # Percent of equity at risk

class RiskManager:
    """
    Manages risk parameters for trades based on account equity and symbol characteristics.
    """

    def __init__(self, risk_per_trade: float = 0.01):
        """
        Initialize the risk manager.

        Args:
            risk_per_trade: Fraction of equity to risk per trade (e.g., 0.01 for 1%)
        """
        self.risk_per_trade = risk_per_trade
        self.logger = logging.getLogger(__name__)

    def calculate_risk(self, symbol: str, signal: int, entry_price: float,
                      atr: float, account_equity: float) -> Optional[TradeRisk]:
        """
        Calculate stop loss, take profit, and lot size based on ATR and account equity.

        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            signal: 1 for BUY, -1 for SELL
            entry_price: Entry price for the trade
            atr: Average True Range (ATR) value for volatility
            account_equity: Current account equity in account currency

        Returns:
            TradeRisk object with calculated SL, TP, and risk amounts, or None if invalid
        """
        if signal == 0:
            self.logger.debug("Signal is NONE, no risk calculation needed")
            return None

        if atr <= 0:
            self.logger.warning(f"Invalid ATR value: {atr}")
            return None

        # Risk amount in account currency
        risk_amount = account_equity * self.risk_per_trade
        self.logger.debug(f"Risk amount: {risk_amount} (equity: {account_equity}, risk%: {self.risk_per_trade})")

        # For now, we use a fixed multiples of ATR for SL and TP
        # These could be made configurable per symbol
        sl_multiplier = 1.5  # ATR multiples for stop loss
        tp_multiplier = 3.0  # ATR multiples for take profit

        if signal == 1:  # BUY
            stop_loss = entry_price - (sl_multiplier * atr)
            take_profit = entry_price + (tp_multiplier * atr)
        elif signal == -1:  # SELL
            stop_loss = entry_price + (sl_multiplier * atr)
            take_profit = entry_price - (tp_multiplier * atr)
        else:
            self.logger.error(f"Invalid signal value: {signal}")
            return None

        # Ensure SL and TP are reasonable (not too close to entry)
        min_distance = 0.0001  # Minimum distance in price terms (1 pip for most forex)
        if abs(entry_price - stop_loss) < min_distance:
            self.logger.warning(f"Calculated SL too close to entry. Adjusting to min distance.")
            if signal == 1:
                stop_loss = entry_price - min_distance
                take_profit = entry_price + (tp_multiplier * min_distance)  # Adjust TP accordingly
            else:
                stop_loss = entry_price + min_distance
                take_profit = entry_price - (tp_multiplier * min_distance)

        trade_risk = TradeRisk(
            symbol=symbol,
            signal=signal,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_amount=risk_amount,
            risk_percent=self.risk_per_trade
        )

        self.logger.info(f"Calculated risk for {symbol}: SL={stop_loss:.5f}, TP={take_profit:.5f}, Risk={risk_amount:.2f}")
        return trade_risk

    def get_symbol_info(self, symbol: str) -> Optional[dict]:
        """
        Get symbol information from MT5.

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary with symbol info or None if not found
        """
        if not mt5.initialize():
            self.logger.error("MT5 initialize failed")
            return None

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            self.logger.error(f"Symbol {symbol} not found")
            mt5.shutdown()
            return None

        # Convert to dictionary
        info = {
            'symbol': symbol,
            'bid': symbol_info.bid,
            'ask': symbol_info.ask,
            'point': symbol_info.point,
            'digits': symbol_info.digits,
            'trade_tick_value': symbol_info.trade_tick_value,
            'trade_tick_size': symbol_info.trade_tick_size,
            'volume_min': symbol_info.volume_min,
            'volume_max': symbol_info.volume_max,
            'volume_step': symbol_info.volume_step,
            'contract_size': symbol_info.trade_contract_size,
            'currency_profit': symbol_info.currency_profit,
            'currency_margin': symbol_info.currency_margin
        }
        mt5.shutdown()
        return info