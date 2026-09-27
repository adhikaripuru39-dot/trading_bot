from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class PositionSize:
    """Represents the calculated position size for a trade"""
    symbol: str
    lot_size: float  # Lot size to trade
    notional_value: float  # Notional value in quote currency
    risk_amount: float  # Amount of money at risk in account currency
    percent_of_equity: float  # Percent of equity used for this trade

class PositionSizer:
    """
    Calculates position size based on risk parameters and symbol characteristics.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def calculate_position_size(self, symbol: str, trade_risk: object,
                               symbol_info: dict, account_equity: float) -> Optional[PositionSize]:
        """
        Calculate the lot size for a trade based on the risk amount and symbol info.

        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            trade_risk: TradeRisk object from risk manager (contains entry, SL, risk_amount)
            symbol_info: Dictionary from get_symbol_info (contains tick value, tick size, etc.)
            account_equity: Current account equity in account currency

        Returns:
            PositionSize object with lot size and notional value, or None if calculation fails
        """
        if trade_risk.signal == 0:
            self.logger.debug("Signal is NONE, no position size needed")
            return None

        # Calculate the risk per pip (or per point) in account currency
        # For forex, the tick value is usually the value of one tick (minimum price move) in the quote currency.
        # We need to convert the risk amount (in account currency) to number of ticks, then to lots.

        # Get the tick value and tick size from symbol_info
        tick_value = symbol_info.get('trade_tick_value')  # Value of one tick in quote currency
        tick_size = symbol_info.get('trade_tick_size')    # Size of one tick in price terms

        if tick_value is None or tick_size is None or tick_value == 0 or tick_size == 0:
            self.logger.error(f"Invalid tick value or size for {symbol}: tick_value={tick_value}, tick_size={tick_size}")
            return None

        # Calculate the price difference between entry and stop loss in price units
        price_risk = abs(trade_risk.entry_price - trade_risk.stop_loss)

        if price_risk <= 0:
            self.logger.error(f"Invalid price risk: {price_risk}")
            return None

        # Convert price risk to number of ticks
        ticks_risk = price_risk / tick_size

        # Calculate the value at risk per lot (in quote currency) for the given stop loss in ticks
        # For a standard lot (1.0), the risk in quote currency would be: ticks_risk * tick_value
        # But note: the tick_value is usually for one tick of the quote currency per lot?
        # Actually, in MT5, trade_tick_value is the value of one tick in the deposit currency for 1 lot.
        # Let's assume that's the case. If not, we may need to adjust.

        # Risk per lot in account currency (deposit currency) = ticks_risk * tick_value
        risk_per_lot = ticks_risk * tick_value

        if risk_per_lot <= 0:
            self.logger.error(f"Calculated risk per lot is zero or negative: {risk_per_lot}")
            return None

        # Calculate the lot size based on the total risk amount we are willing to take
        lot_size = trade_risk.risk_amount / risk_per_lot

        # Apply lot step (minimum lot size increment) from symbol_info
        lot_step = symbol_info.get('volume_step', 0.01)  # Default to 0.01 if not provided
        lot_min = symbol_info.get('volume_min', 0.01)
        lot_max = symbol_info.get('volume_max', 100.0)

        # Round down to the nearest lot step
        lot_size = (lot_size // lot_step) * lot_step

        # Ensure lot size is within min and max
        if lot_size < lot_min:
            self.logger.warning(f"Calculated lot size {lot_size} is below minimum {lot_min}. Setting to minimum.")
            lot_size = lot_min
        elif lot_size > lot_max:
            self.logger.warning(f"Calculated lot size {lot_size} is above maximum {lot_max}. Setting to maximum.")
            lot_size = lot_max

        # Recalculate the actual risk amount based on the lot size (since we rounded)
        actual_risk_amount = lot_size * risk_per_lot

        # Calculate notional value (for reference) - not directly used in trading but useful for logging
        # Notional value = lot_size * contract_size * entry_price (approx)
        contract_size = symbol_info.get('contract_size', 100000)  # Default for forex
        notional_value = lot_size * contract_size * trade_risk.entry_price

        # Percent of equity used (for reference)
        percent_of_equity = (actual_risk_amount / account_equity) * 100 if account_equity > 0 else 0

        position_size = PositionSize(
            symbol=symbol,
            lot_size=lot_size,
            notional_value=notional_value,
            risk_amount=actual_risk_amount,
            percent_of_equity=percent_of_equity
        )

        self.logger.info(
            f"Position size for {symbol}: lot={lot_size:.2f}, risk={actual_risk_amount:.2f} "
            f"({percent_of_equity:.2f}% of equity), notional={notional_value:.2f}"
        )

        return position_size