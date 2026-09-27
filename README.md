# Prop Firm Algorithmic Trading Bot

A robust, Python-based algorithmic trading framework designed to integrate with MetaTrader 5 (MT5). This bot is specifically tailored to meet the strict risk management standards of proprietary trading firms like **Funded Next**.

## Features
- **Modular Architecture:** Clear separation of Data Engine, Signal Engine, Risk Manager, and Execution Engine.
- **Scientific Backtesting:** Replicate live market outcomes by feeding historical data through the exact same signal and risk logic used in live trading.
- **Prop Firm Safeguards:** Built-in Daily Drawdown (e.g., 5%) and Maximum Drawdown (e.g., 10%) monitors.
- **News Filter:** Halt trading before and after high-impact economic news events to avoid slippage and prop firm rule violations.

---

## 1. How to Carry Out a Backtest

Backtesting allows you to test your strategy scientifically against historical data without risking real money. The backtester uses a mocked MT5 interface, meaning you do not need MT5 installed to run it.

### Prerequisites
Make sure you have installed the requirements:
```bash
pip install -r requirements.txt
```

### Running the Backtest
1. **Prepare Data:** The `backtest.py` script currently includes dummy data for demonstration. For real backtesting, export OHLCV (Open, High, Low, Close, Volume) M1 data from your MT5 terminal to a CSV.
2. **Update Script:** Modify the `__main__` block in `backtest.py` to read your CSV data using Pandas and format it into the `dummy_data` dictionary structure.
3. **Run:**
   ```bash
   python backtest.py
   ```
4. **Review Results:** The script will output trades to the console and save an equity curve to `backtest_equity_curve.png`.

---

## 2. How to Run in Live Trading Mode

To run the bot in live trading mode, it must be executed on a Windows machine (or a Windows VPS) with the MetaTrader 5 desktop terminal installed and logged into your Funded Next account.

### Setup
1. **Install Python for Windows.**
2. **Install MT5 and the Python Integration:**
   ```cmd
   pip install MetaTrader5 pandas pyyaml numpy matplotlib
   ```
3. **Configure the Bot:** Edit the `config.yaml` file to set your symbols, risk per trade, moving average periods, and MT5 Magic Number.
4. **Configure News Filter:** In `bot.py`, implement a method to fetch live calendar events and pass them into `self.news_filter.load_events()`.

### Execution
1. Open your MT5 terminal and ensure "Allow Algorithmic Trading" is enabled.
2. Run the bot:
   ```cmd
   python bot.py
   ```
3. The bot will continuously monitor ticks, generate bars, calculate signals, and place trades while monitoring your daily/max drawdowns.

---

## 3. VPS Deployment Guide

For algorithmic trading, especially with prop firms, 100% uptime is required. Running the bot on your personal laptop is risky due to power outages or internet drops.

### Recommended VPS Specs
- **OS:** Windows Server 2019 or 2022 (MT5 Python integration relies on Windows C++ libraries).
- **RAM:** Minimum 2GB (4GB recommended for running MT5 + Python smoothly).
- **Location:** Choose a VPS data center located close to your broker's servers (e.g., London, New York) to minimize execution latency.

### Deployment Steps
1. **Purchase and Connect:** Rent a Windows VPS (e.g., AWS EC2, Vultr, ForexVPS) and connect via Remote Desktop Connection (RDP).
2. **Install Software:** Download and install your broker's MetaTrader 5 terminal, Python, and Git.
3. **Clone Repository:** Clone this repository to the VPS.
4. **Install Dependencies:** Run `pip install -r requirements.txt` (Ensure `MetaTrader5` installs successfully).
5. **Setup Auto-Start (Crucial for Prop Firms):**
   - Press `Win + R`, type `shell:startup`, and hit Enter.
   - Create a batch file (`run_bot.bat`) in this folder.
   - Add the following code to the batch file to ensure MT5 and the Python bot launch automatically if the VPS reboots:
     ```bat
     @echo off
     start "" "C:\Program Files\YourBroker MT5\terminal64.exe"
     timeout /t 30
     cd C:\path\to\your\bot
     python bot.py
     ```
6. **Monitor:** Use the generated `logs/trades.csv` and `logs/bot.log` files to monitor performance. Periodically check your Prop Firm dashboard to ensure the bot's PnL aligns with the firm's metrics.