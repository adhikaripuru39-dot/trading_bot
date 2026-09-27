# Trading Bot Assessment for Prop Firm (Funded Next)

## Overview
This document assesses the existing Python-based MetaTrader 5 trading bot framework to evaluate its suitability for use with a proprietary trading firm such as Funded Next. It outlines the strengths, weaknesses, required add-ons to meet prop firm standards, and the methodology for implementing these changes while preserving a scientific trading approach.

## 1. Assessment of the Current Framework

### Pros (The "Goods")
- **Modular Architecture:** The system is cleanly divided into components (`DataEngine`, `SignalEngine`, `RiskManager`, `PositionSizer`, `Monitor`, `bot.py`). This allows for easy swapping of strategies and risk models.
- **Scientific Approach:** The use of `pandas` for handling tick/bar data and generating signals aligns with a quantitative and scientific trading approach. This structure makes it highly conducive to accurate backtesting.
- **Risk Management Base:** The `RiskManager` and `PositionSizer` are designed to calculate lot sizes based on account equity, ATR (Average True Range), and a fixed risk percentage per trade. This is foundational for survival in prop firms.
- **Monitoring & Logging:** The existing `Monitor` class is well-set up to log trades to a CSV file and track the equity curve, which is essential for performance review and backtest validation.

### Cons (The "Bads" / Room for Improvement)
- **Missing Execution Engine:** The `execution_engine.py` is missing from the repository, meaning the bot cannot actually place trades in its current state.
- **No Prop Firm Safeguards:** The bot lacks mechanisms to monitor Daily Drawdown (e.g., 5% limit) and Maximum Drawdown (e.g., 10% limit). Breaching these limits results in immediate account loss at a prop firm.
- **No News Filter:** Prop firms often restrict trading during high-impact news events (e.g., NFP, CPI). Trading during these times can lead to slippage, spread widening, or outright account termination depending on the firm's rules.
- **Hardcoded Dependencies:** The bot relies heavily on the `MetaTrader5` library being initialized and connected. To achieve a true scientific approach, the system needs a dedicated backtesting module that bypasses MT5 to simulate historical performance accurately.
- **Weekend/Session Management:** There is no logic to close positions before the weekend or at the end of a trading session, which is a common requirement for some funded accounts.

## 2. Required Add-ons for Prop Firm Standards

To safely trade a Funded Next account, the following add-ons are mandatory:

1. **Daily Drawdown Manager:**
   - **Purpose:** Monitor the account balance and equity. If the equity falls below a certain percentage (e.g., 5%) of the *daily starting balance*, trading must halt, and open positions should ideally be closed to prevent breaching the limit.
   - **Pros:** Saves the account from being blown in a single bad day.
   - **Cons:** Might prematurely stop trading on a day that could have recovered.

2. **Maximum Drawdown Manager:**
   - **Purpose:** Ensure the account equity never falls below a fixed percentage (e.g., 10%) of the *initial account balance*.
   - **Pros:** Ensures long-term survival of the account.
   - **Cons:** Restricts risk-taking as the account approaches the threshold.

3. **News Filter:**
   - **Purpose:** Prevent new trades from being opened and potentially manage existing trades $X$ minutes before and after high-impact economic news.
   - **Pros:** Avoids extreme volatility, slippage, and prop firm rule violations.
   - **Cons:** Requires integration with an external API (like Forex Factory) or a static economic calendar file.

4. **Backtesting Engine:**
   - **Purpose:** Replicate the live market environment using historical data to validate strategies scientifically.

## 3. Methodology for Implementation

To ensure these add-ons do not have adverse effects on the existing framework, they should be implemented using a **Decorator/Interceptor pattern** within the main trading loop.

### Methodology:
1. **Develop Isolated Modules:** Create `prop_firm_manager.py` and `news_filter.py` as independent classes that do not modify the core `SignalEngine` or `ExecutionEngine`.
2. **Pre-Trade Checks:** In `bot.py`, before a signal is processed or an order is placed, query these new modules.
   ```python
   if not self.prop_firm_manager.is_trading_allowed(current_equity):
       return # Halt trading
   if not self.news_filter.is_trading_allowed(symbol, current_time):
       return # Skip due to news
   ```
3. **Mocking for Backtests:** Create a `MockExecutionEngine` and feed historical OHLCV data into the `DataEngine` sequentially. By doing this, the exact same signal generation logic is used in backtesting as in live trading, ensuring the live market replicates the backtest outcomes.
