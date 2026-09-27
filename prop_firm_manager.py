import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PropFirmManager:
    """
    Manages daily and maximum drawdowns according to prop firm rules.
    """
    def __init__(self, initial_balance: float, daily_dd_limit: float = 0.05, max_dd_limit: float = 0.10):
        self.initial_balance = initial_balance
        self.daily_dd_limit = daily_dd_limit
        self.max_dd_limit = max_dd_limit

        self.daily_starting_balance = initial_balance
        self.current_date = datetime.now().date()
        self.trading_halted = False
        self.logger = logging.getLogger(__name__)

    def update_daily_balance(self, current_balance: float, date: datetime.date):
        """Update daily starting balance if a new day has started."""
        if date > self.current_date:
            self.current_date = date
            self.daily_starting_balance = current_balance
            self.trading_halted = False  # Reset halt on a new day
            self.logger.info(f"New day started. Daily starting balance updated to {self.daily_starting_balance}")

    def is_trading_allowed(self, current_equity: float, current_balance: float, current_time: datetime) -> bool:
        """
        Check if trading is allowed based on current equity and balances.
        """
        if self.trading_halted:
            return False

        # Update daily balance if day has rolled over
        self.update_daily_balance(current_balance, current_time.date())

        # Check Max Drawdown
        max_dd_threshold = self.initial_balance * (1 - self.max_dd_limit)
        if current_equity <= max_dd_threshold:
            self.logger.critical(f"MAX DRAWDOWN BREACHED! Equity: {current_equity} <= Threshold: {max_dd_threshold}")
            self.trading_halted = True
            return False

        # Check Daily Drawdown
        daily_dd_threshold = self.daily_starting_balance * (1 - self.daily_dd_limit)
        if current_equity <= daily_dd_threshold:
            self.logger.critical(f"DAILY DRAWDOWN BREACHED! Equity: {current_equity} <= Threshold: {daily_dd_threshold}")
            self.trading_halted = True
            return False

        return True
