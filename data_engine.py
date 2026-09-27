import pandas as pd
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

@dataclass
class Bar:
    """Represents a single OHLCV bar"""
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str

class DataEngine:
    """
    Handles ingestion and processing of tick data into time-aligned bars.
    Designed to work with MT5 tick data exports.
    """

    def __init__(self, symbol: str):
        self.symbol = symbol
        self._buffer = []  # Temporary buffer for ticks within current minute
        self.last_bar_time = None
        self.logger = logging.getLogger(f"{__name__}.{symbol}")

    def process_tick(self, tick: Dict) -> Optional[Bar]:
        """
        Process a single tick and return a completed bar if the minute has elapsed.

        Args:
            tick: Dictionary with keys 'time', 'bid', 'ask', 'volume'
                  Expected format from MT5: {'time': datetime, 'bid': float, 'ask': float, 'volume': int}

        Returns:
            Bar object if a minute bar is completed, None otherwise
        """
        # Use mid-price for simplicity
        price = (tick['bid'] + tick['ask']) / 2
        volume = tick.get('volume', 1)  # Default volume if not provided
        tick_time = tick['time']

        # Ensure timezone awareness
        if tick_time.tzinfo is None:
            tick_time = tick_time.replace(tzinfo=timezone.utc)

        # Round down to minute boundary
        minute_floor = tick_time.replace(second=0, microsecond=0)

        # If we've moved to a new minute, finalize the previous bar
        if self.last_bar_time is not None and minute_floor > self.last_bar_time:
            bar = self._create_bar(self.last_bar_time)
            self.last_bar_time = minute_floor
            self._buffer = [{'price': price, 'volume': volume}]
            self.logger.debug(f"Completed bar: {bar}")
            return bar
        elif self.last_bar_time is None:
            # First tick
            self.last_bar_time = minute_floor
            self._buffer = [{'price': price, 'volume': volume}]
        else:
            # Same minute, add to buffer
            self._buffer.append({'price': price, 'volume': volume})

        return None

    def _create_bar(self, bar_time: datetime) -> Bar:
        """Create OHLCV bar from buffered ticks"""
        if not self._buffer:
            # Should not happen, but handle gracefully
            return Bar(
                time=bar_time,
                open=0.0, high=0.0, low=0.0, close=0.0, volume=0.0,
                symbol=self.symbol
            )

        prices = [tick['price'] for tick in self._buffer]
        volumes = [tick['volume'] for tick in self._buffer]

        return Bar(
            time=bar_time,
            open=prices[0],
            high=max(prices),
            low=min(prices),
            close=prices[-1],
            volume=sum(volumes),
            symbol=self.symbol
        )

    def flush(self) -> Optional[Bar]:
        """
        Flush any remaining ticks as a bar (call at end of data).

        Returns:
            Bar object if there's buffered data, None otherwise
        """
        if self._buffer and self.last_bar_time is not None:
            bar = self._create_bar(self.last_bar_time)
            self._buffer = []
            self.logger.debug(f"Flushed bar: {bar}")
            return bar
        return None

    @staticmethod
    def resample_tick_data(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        Alternative method: resample a DataFrame of tick data to 1-minute bars.
        Useful for backtesting with historical data.

        Args:
            df: DataFrame with columns ['time', 'bid', 'ask', 'volume']
            symbol: Trading symbol

        Returns:
            DataFrame with OHLCV bars indexed by time
        """
        # Ensure time column is datetime
        df = df.copy()
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)

        # Calculate mid-price
        df['mid_price'] = (df['bid'] + df['ask']) / 2

        # Resample to 1-minute OHLCV
        ohlc = df['mid_price'].resample('1min').ohlc()
        ohlc.columns = ['open', 'high', 'low', 'close']
        volume = df['volume'].resample('1min').sum()

        # Combine
        bars = pd.concat([ohlc, volume], axis=1)
        bars.dropna(inplace=True)  # Remove empty periods
        bars['symbol'] = symbol

        return bars