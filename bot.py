import time
import yaml
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import MetaTrader5 as mt5

# Import our custom modules
from data_engine import DataEngine, Bar
from signal_engine import create_signal_engine, SignalResult
from risk_manager import RiskManager, TradeRisk
from position_sizer import PositionSizer, PositionSize
from execution_engine import ExecutionEngine, TradeOrder, TradeResult
from monitor import Monitor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingBot:
    """
    Main trading bot orchestrator.
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the trading bot.

        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.symbols = [pair['symbol'] for pair in self.config['pairs']]
        self.data_engines: Dict[str, DataEngine] = {}
        self.signal_engines: Dict[str, object] = {}  # Will hold SignalEngine instances
        self.bar_history: Dict[str, pd.DataFrame] = {}  # History of bars for each symbol
        self.risk_manager = RiskManager(risk_per_trade=self.config['risk_per_trade'])
        self.position_sizer = PositionSizer()
        self.execution_engine = ExecutionEngine(magic_number=self.config['execution']['magic_number'])
        self.monitor = Monitor(self.config)

        # State tracking
        self.open_positions: Dict[int, Dict] = {}  # ticket -> position info
        self.account_equity = 0.0
        self.is_running = False

        # Initialize components
        self._initialize_components()

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def _initialize_components(self):
        """Initialize MT5 connection and per-symbol components."""
        # Initialize MT5
        if not mt5.initialize():
            logger.error("Failed to initialize MT5")
            raise ConnectionError("Could not connect to MetaTrader5")

        logger.info("MetaTrader5 initialized successfully")

        # Get initial account equity
        self._update_account_equity()

        # Initialize data and signal engines for each symbol
        for symbol in self.symbols:
            self.data_engines[symbol] = DataEngine(symbol)

            # Find pair config for this symbol
            pair_config = next((p for p in self.config['pairs'] if p['symbol'] == symbol), None)
            if pair_config is None:
                logger.error(f"No configuration found for symbol {symbol}")
                continue

            # Create signal engine
            self.signal_engines[symbol] = create_signal_engine(symbol, pair_config['signal'])

            # Initialize bar history (we'll start with empty and fill as we get bars)
            self.bar_history[symbol] = pd.DataFrame(columns=['time', 'open', 'high', 'low', 'close', 'volume'])

            logger.info(f"Initialized components for {symbol}")

        # Initialize execution engine
        if not self.execution_engine.initialize():
            logger.error("Failed to initialize execution engine")
            mt5.shutdown()
            raise ConnectionError("Could not initialize execution engine")

        logger.info("All components initialized")

    def _update_account_equity(self):
        """Update account equity from MT5."""
        try:
            account_info = mt5.account_info()
            if account_info is not None:
                self.account_equity = account_info.equity
                logger.debug(f"Account equity updated: {self.account_equity}")
            else:
                logger.warning("Could not get account info")
        except Exception as e:
            logger.error(f"Error updating account equity: {e}")

    def _get_latest_tick(self, symbol: str) -> Optional[Dict]:
        """Get the latest tick for a symbol from MT5."""
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.warning(f"No tick data for {symbol}")
                return None

            return {
                'time': datetime.fromtimestamp(tick.time),
                'bid': tick.bid,
                'ask': tick.ask,
                'volume': tick.volume if hasattr(tick, 'volume') else 0
            }
        except Exception as e:
            logger.error(f"Error getting tick for {symbol}: {e}")
            return None

    def _update_bar_history(self, symbol: str, new_bar: Bar):
        """Update the bar history for a symbol with a new bar."""
        # Convert Bar to dict for DataFrame
        bar_dict = {
            'time': new_bar.time,
            'open': new_bar.open,
            'high': new_bar.high,
            'low': new_bar.low,
            'close': new_bar.close,
            'volume': new_bar.volume
        }

        # Append to history
        new_row = pd.DataFrame([bar_dict])
        self.bar_history[symbol] = pd.concat([self.bar_history[symbol], new_row], ignore_index=True)

        # Keep only recent bars (e.g., last 500 bars) to limit memory usage
        max_bars = 500
        if len(self.bar_history[symbol]) > max_bars:
            self.bar_history[symbol] = self.bar_history[symbol].tail(max_bars)

        logger.debug(f"Updated bar history for {symbol}. Total bars: {len(self.bar_history[symbol])}")

    def _process_symbol(self, symbol: str):
        """Process a single symbol: get tick, update bar, generate signal, manage trade."""
        logger.debug(f"Processing {symbol}")

        # Get latest tick
        tick = self._get_latest_tick(symbol)
        if tick is None:
            return

        # Feed tick to data engine to get a new bar (if minute completed)
        data_engine = self.data_engines[symbol]
        new_bar = data_engine.process_tick(tick)

        # If we got a new bar, update history and generate signal
        if new_bar is not None:
            self._update_bar_history(symbol, new_bar)
            self._generate_and_process_signal(symbol, new_bar.time)

        # Flush any remaining bars at the end of each minute? (Optional, handled by process_tick)

    def _generate_and_process_signal(self, symbol: str, bar_time: datetime):
        """Generate signal for symbol and process if actionable."""
        # Get signal engine
        signal_engine = self.signal_engines[symbol]

        # Get bar history (need enough for indicators)
        bars = self.bar_history[symbol]
        if len(bars) < 50:  # Need at least some bars for indicators
            logger.debug(f"Not enough bars for {symbol} to generate signal")
            return

        # Calculate signal
        signal_result: SignalResult = signal_engine.calculate_signal(bars)

        # Log the signal
        self.monitor.log_signal(symbol, signal_result, bar_time)

        # If signal is NONE, do nothing
        if signal_result.signal.name == 'NONE':
            return

        logger.info(f"Signal for {symbol}: {signal_result.signal.name} (strength: {signal_result.strength:.3f})")

        # Get latest bar price for entry
        latest_bar = bars.iloc[-1]
        entry_price = latest_bar['close']

        # Calculate ATR for risk management (we'll compute it here for simplicity)
        # In a more refined design, the signal engine could return ATR as part of metadata
        atr = self._calculate_atr(bars, period=14)
        if atr is None or atr <= 0:
            logger.warning(f"Could not calculate ATR for {symbol}")
            return

        # Calculate risk parameters
        trade_risk = self.risk_manager.calculate_risk(
            symbol=symbol,
            signal=1 if signal_result.signal.name == 'BUY' else -1,
            entry_price=entry_price,
            atr=atr,
            account_equity=self.account_equity
        )

        if trade_risk is None:
            logger.warning(f"Risk calculation failed for {symbol}")
            return

        # Calculate position size
        # Get symbol info from MT5
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logger.error(f"Could not get symbol info for {symbol}")
            return

        symbol_info_dict = {
            'trade_tick_value': symbol_info.trade_tick_value,
            'trade_tick_size': symbol_info.trade_tick_size,
            'volume_min': symbol_info.volume_min,
            'volume_max': symbol_info.volume_max,
            'volume_step': symbol_info.volume_step,
            'contract_size': symbol_info.trade_contract_size
        }

        position_size = self.position_sizer.calculate_position_size(
            symbol=symbol,
            trade_risk=trade_risk,
            symbol_info=symbol_info_dict,
            account_equity=self.account_equity
        )

        if position_size is None or position_size.lot_size <= 0:
            logger.warning(f"Position sizing failed or resulted in zero lot size for {symbol}")
            return

        # Create trade order
        order = TradeOrder(
            symbol=symbol,
            lot_size=position_size.lot_size,
            order_type='buy' if trade_risk.signal == 1 else 'sell',
            price=entry_price,  # Will be overridden by execution engine with current market price
            stop_loss=trade_risk.stop_loss,
            take_profit=trade_risk.take_profit,
            magic_number=self.config['execution']['magic_number'],
            comment=f"SignalStrength_{signal_result.strength:.2f}"
        )

        # Execute trade
        logger.info(f"Placing {order.order_type} order for {symbol}: {position_size.lot_size} lots")
        trade_result = self.execution_engine.place_market_order(order)

        # Log the trade attempt
        if trade_result.success:
            self.monitor.log_trade(
                symbol=symbol,
                signal=order.order_type.upper(),
                lot_size=position_size.lot_size,
                entry_price=trade_result.price,
                stop_loss=trade_risk.stop_loss,
                take_profit=trade_risk.take_profit,
                order_id=trade_result.order_id,
                status='OPEN',
                comment=order.comment
            )
            # Track open position
            self.open_positions[trade_result.order_id] = {
                'symbol': symbol,
                'signal': order.order_type.upper(),
                'lot_size': position_size.lot_size,
                'open_time': datetime.now(),
                'initial_sl': trade_risk.stop_loss,
                'initial_tp': trade_risk.take_profit
            }
        else:
            self.monitor.log_trade(
                symbol=symbol,
                signal=order.order_type.upper(),
                lot_size=position_size.lot_size,
                entry_price=entry_price,
                stop_loss=trade_risk.stop_loss,
                take_profit=trade_risk.take_profit,
                order_id=None,
                status='FAILED',
                comment=f"Error: {trade_result.error_description}"
            )

    def _calculate_atr(self, bars: pd.DataFrame, period: int = 14) -> Optional[float]:
        """Calculate Average True Range from OHLC data."""
        if len(bars) < period:
            return None

        high_low = bars['high'] - bars['low']
        high_close = (bars['high'] - bars['close'].shift()).abs()
        low_close = (bars['low'] - bars['close'].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean().iloc[-1]
        return atr

    def _manage_open_positions(self):
        """Check and manage open positions (e.g., trailing stop, manual close on opposite signal)."""
        # In this version, we rely on the SL/TP set in the order.
        # We could add logic to move stop loss to break-even, trail, etc.
        # For now, we just log and let MT5 handle it.
        pass

    def _update_account_info(self):
        """Update account equity and check for margin calls, etc."""
        self._update_account_equity()
        # Could also check margin, free margin, etc.

    def run(self):
        """Main trading loop."""
        logger.info("Starting trading bot...")
        self.is_running = True

        try:
            while self.is_running:
                start_time = time.time()

                # Update account info
                self._update_account_info()

                # Process each symbol
                for symbol in self.symbols:
                    self._process_symbol(symbol)

                # Manage open positions
                self._manage_open_positions()

                # Sleep to avoid excessive CPU usage
                elapsed = time.time() - start_time
                sleep_time = max(0.1, 1.0 - elapsed)  # Aim for ~1 second loop
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
        finally:
            self.shutdown()

    def shutdown(self):
        """Shutdown the bot and clean up resources."""
        logger.info("Shutting down trading bot...")
        self.is_running = False

        # Shutdown execution engine
        self.execution_engine.shutdown()

        # Shutdown MT5
        mt5.shutdown()
        logger.info("MetaTrader5 shutdown")

        # Save any final reports
        self.monitor.save_equity_curve()
        logger.info("Trading bot stopped")

if __name__ == "__main__":
    # Create and run the bot
    bot = TradingBot()
    bot.run()