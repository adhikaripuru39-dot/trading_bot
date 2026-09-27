import pandas as pd
import numpy as np
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class Signal(Enum):
    """Trading signal types"""
    NONE = 0
    BUY = 1
    SELL = 2

@dataclass
class SignalResult:
    """Result from signal engine"""
    signal: Signal
    strength: float  # 0.0 to 1.0 indicating confidence
    metadata: Dict[str, Any]  # Additional info like indicator values

class SignalEngine(ABC):
    """Abstract base class for signal engines"""

    def __init__(self, symbol: str, config: Dict[str, Any]):
        self.symbol = symbol
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{symbol}")
        self.logger.debug(f"Initialized signal engine with config: {config}")

    @abstractmethod
    def calculate_signal(self, bars: pd.DataFrame) -> SignalResult:
        """
        Calculate trading signal based on historical bars.

        Args:
            bars: DataFrame with OHLCV data indexed by time

        Returns:
            SignalResult object
        """
        pass

class SMACrossover(SignalEngine):
    """
    Simple Moving Average Crossover strategy with ATR filter.
    Goes long when fast MA crosses above slow MA, short when fast MA crosses below slow MA.
    Only takes signals when ATR is above a threshold (indicating sufficient volatility).
    """

    def __init__(self, symbol: str, config: Dict[str, Any]):
        super().__init__(symbol, config)
        self.fast_period = config.get('fast', 50)
        self.slow_period = config.get('slow', 200)
        self.atr_period = config.get('atr_period', 14)
        self.atr_multiplier = config.get('atr_multiplier', 0.5)  # Minimum ATR as percentage of price

        self.logger.info(f"SMACrossover initialized: fast={self.fast_period}, slow={self.slow_period}")

    def calculate_signal(self, bars: pd.DataFrame) -> SignalResult:
        """Calculate SMA crossover signal with ATR filter"""
        if len(bars) < max(self.fast_period, self.slow_period, self.atr_period) + 1:
            return SignalResult(Signal.NONE, 0.0, {"reason": "insufficient_data"})

        # Calculate moving averages
        bars = bars.copy()
        bars['fast_ma'] = bars['close'].rolling(window=self.fast_period).mean()
        bars['slow_ma'] = bars['close'].rolling(window=self.slow_period).mean()

        # Calculate ATR (Average True Range)
        high_low = bars['high'] - bars['low']
        high_close = np.abs(bars['high'] - bars['close'].shift())
        low_close = np.abs(bars['low'] - bars['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        bars['atr'] = true_range.rolling(window=self.atr_period).mean()

        # Get latest values
        latest = bars.iloc[-1]
        previous = bars.iloc[-2]

        # Check for crossover signals
        fast_above_slow = latest['fast_ma'] > latest['slow_ma']
        prev_fast_above_slow = previous['fast_ma'] > previous['slow_ma']

        # ATR filter - only trade when volatility is sufficient
        atr_ratio = latest['atr'] / latest['close'] if latest['close'] > 0 else 0
        volatility_sufficient = atr_ratio > self.atr_multiplier

        signal = Signal.NONE
        strength = 0.0
        reason = ""

        # Bullish crossover: fast MA crosses above slow MA
        if not prev_fast_above_slow and fast_above_slow and volatility_sufficient:
            signal = Signal.BUY
            # Strength based on how strong the crossover is and volatility
            ma_diff = (latest['fast_ma'] - latest['slow_ma']) / latest['close']
            strength = min(1.0, abs(ma_diff) * 100)  # Scale to 0-1 range
            strength = max(0.1, strength)  # Minimum strength for valid signal
            reason = "bullish_crossover"

        # Bearish crossover: fast MA crosses below slow MA
        elif prev_fast_above_slow and not fast_above_slow and volatility_sufficient:
            signal = Signal.SELL
            ma_diff = (latest['slow_ma'] - latest['fast_ma']) / latest['close']
            strength = min(1.0, abs(ma_diff) * 100)
            strength = max(0.1, strength)
            reason = "bearish_crossover"

        else:
            reason = "no_crossover" if not volatility_sufficient else "insufficient_volatility"

        metadata = {
            "fast_ma": latest['fast_ma'],
            "slow_ma": latest['slow_ma'],
            "atr": latest['atr'],
            "atr_ratio": atr_ratio,
            "price": latest['close'],
            "reason": reason
        }

        self.logger.debug(f"Signal calculation: {signal.name}, strength={strength:.3f}, {metadata}")

        return SignalResult(signal, strength, metadata)

def create_signal_engine(symbol: str, config: Dict[str, Any]) -> SignalEngine:
    """Factory function to create signal engines based on config"""
    engine_type = config.get('type', 'sma_crossover').lower()

    if engine_type == 'sma_crossover':
        return SMACrossover(symbol, config)
    else:
        raise ValueError(f"Unsupported signal engine type: {engine_type}")