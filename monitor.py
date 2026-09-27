import logging
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import matplotlib.pyplot as plt
import pandas as pd

class Monitor:
    """
    Handles logging, monitoring, and reporting for the trading bot.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the monitor.

        Args:
            config: Configuration dictionary containing logging settings
        """
        self.config = config
        self.log_file = Path(config.get('logging', {}).get('file', 'logs/bot.log'))
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self.logger = logging.getLogger('TradingBotMonitor')
        self.logger.setLevel(getattr(logging, config.get('logging', {}).get('level', 'INFO')))

        # File handler
        fh = logging.FileHandler(self.log_file)
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

        # Console handler (optional)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

        # Trade log file (CSV)
        self.trade_log_file = self.log_file.parent / 'trades.csv'
        self._init_trade_log()

        # Equity curve data
        self.equity_data = []  # List of (timestamp, equity) tuples

        self.logger.info("Monitor initialized")

    def _init_trade_log(self):
        """Initialize the trade log CSV file with headers if it doesn't exist"""
        if not self.trade_log_file.exists():
            with open(self.trade_log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'symbol', 'signal', 'lot_size', 'entry_price',
                    'stop_loss', 'take_profit', 'order_id', 'status', 'pnl',
                    'comment'
                ])

    def log_signal(self, symbol: str, signal_result: Any, bar_time: datetime):
        """
        Log a trading signal.

        Args:
            symbol: Trading symbol
            signal_result: SignalResult object from signal engine
            bar_time: Time of the bar that generated the signal
        """
        self.logger.info(
            f"SIGNAL - {symbol}: {signal_result.signal.name} "
            f"(strength: {signal_result.strength:.3f}) at {bar_time}"
        )
        # Could also log to a separate signals file if needed

    def log_trade(self, symbol: str, signal: str, lot_size: float, entry_price: float,
                  stop_loss: float, take_profit: float, order_id: Optional[int],
                  status: str, pnl: float = 0.0, comment: str = ""):
        """
        Log a trade to the trade log CSV.

        Args:
            symbol: Trading symbol
            signal: 'BUY' or 'SELL'
            lot_size: Lot size traded
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            order_id: MT5 order ticket ID
            status: 'OPEN', 'CLOSED', 'FAILED'
            pnl: Profit/loss in account currency (for closed trades)
            comment: Additional comment
        """
        timestamp = datetime.now().isoformat()
        with open(self.trade_log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp, symbol, signal, lot_size, entry_price,
                stop_loss, take_profit, order_id, status, pnl, comment
            ])

        self.logger.info(
            f"TRADE - {symbol}: {signal} {lot_size} lots @ {entry_price:.5f} "
            f"SL:{stop_loss:.5f} TP:{take_profit:.5f} Ticket:{order_id} {status}"
        )

    def update_equity(self, timestamp: datetime, equity: float):
        """
        Update equity curve data.

        Args:
            timestamp: Time of equity update
            equity: Current account equity
        """
        self.equity_data.append((timestamp, equity))
        self.logger.debug(f"Equity update: {timestamp} - {equity:.2f}")

    def save_equity_curve(self, filename: Optional[str] = None):
        """
        Save equity curve as a PNG chart.

        Args:
            filename: Optional filename, defaults to equity_curve.png in logs directory
        """
        if len(self.equity_data) < 2:
            self.logger.warning("Not enough data to plot equity curve")
            return

        if filename is None:
            filename = self.log_file.parent / 'equity_curve.png'
        else:
            filename = Path(filename)

        # Convert to DataFrame for easier plotting
        df = pd.DataFrame(self.equity_data, columns=['timestamp', 'equity'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        plt.figure(figsize=(12, 6))
        plt.plot(df['timestamp'], df['equity'])
        plt.title('Equity Curve')
        plt.xlabel('Time')
        plt.ylabel('Equity')
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()

        self.logger.info(f"Equity curve saved to {filename}")

    def generate_daily_report(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Generate a daily performance report.

        Args:
            date: Date for report (defaults to today)

        Returns:
            Dictionary with report metrics
        """
        if date is None:
            date = datetime.now().date()
        else:
            date = date.date()

        # Read trade log for the specified date
        if not self.trade_log_file.exists():
            return {"error": "No trade log found"}

        trades = []
        with open(self.trade_log_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                trade_date = datetime.fromisoformat(row['timestamp']).date()
                if trade_date == date:
                    trades.append(row)

        if not trades:
            return {"date": date.isoformat(), "trades": 0, "message": "No trades for this date"}

        # Calculate metrics
        total_trades = len(trades)
        closed_trades = [t for t in trades if t['status'] == 'CLOSED' and float(t['pnl']) != 0]
        winning_trades = [t for t in closed_trades if float(t['pnl']) > 0]
        losing_trades = [t for t in closed_trades if float(t['pnl']) < 0]

        total_pnl = sum(float(t['pnl']) for t in closed_trades)
        win_rate = len(winning_trades) / len(closed_trades) * 100 if closed_trades else 0
        avg_win = sum(float(t['pnl']) for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(float(t['pnl']) for t in losing_trades) / len(losing_trades) if losing_trades else 0
        profit_factor = abs(avg_win * len(winning_trades) / (avg_loss * len(losing_trades))) if avg_loss != 0 and losing_trades else 0

        report = {
            "date": date.isoformat(),
            "total_trades": total_trades,
            "closed_trades": len(closed_trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": round(win_rate, 2),
            "total_pnl": round(total_pnl, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2)
        }

        self.logger.info(f"Daily report for {date}: {json.dumps(report, indent=2)}")
        return report

    def log_info(self, message: str):
        """Log an info message"""
        self.logger.info(message)

    def log_warning(self, message: str):
        """Log a warning message"""
        self.logger.warning(message)

    def log_error(self, message: str):
        """Log an error message"""
        self.logger.error(message)

    def log_debug(self, message: str):
        """Log a debug message"""
        self.logger.debug(message)