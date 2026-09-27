import pandas as pd
from datetime import datetime, timezone, timedelta
from data_engine import DataEngine, Bar

def test_data_engine():
    """Test the DataEngine with simulated tick data."""
    print("Testing DataEngine...")

    # Create a data engine for EURUSD
    engine = DataEngine("EURUSD")

    # Simulate ticks within a minute
    base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Tick 1: at 12:00:00
    tick1 = {
        'time': base_time,
        'bid': 1.1000,
        'ask': 1.1002,
        'volume': 10
    }

    # Tick 2: at 12:00:30
    tick2 = {
        'time': base_time + timedelta(seconds=30),
        'bid': 1.1005,
        'ask': 1.1007,
        'volume': 15
    }

    # Tick 3: at 12:00:45
    tick3 = {
        'time': base_time + timedelta(seconds=45),
        'bid': 1.1003,
        'ask': 1.1005,
        'volume': 7
    }

    # Tick 4: at 12:01:10 (next minute)
    tick4 = {
        'time': base_time + timedelta(minutes=1, seconds=10),
        'bid': 1.1010,
        'ask': 1.1012,
        'volume': 20
    }

    # Process ticks
    bar1 = engine.process_tick(tick1)
    bar2 = engine.process_tick(tick2)
    bar3 = engine.process_tick(tick3)
    bar4 = engine.process_tick(tick4)  # This should return the completed bar for the first minute

    print(f"Bar after tick1: {bar1}")  # Should be None
    print(f"Bar after tick2: {bar2}")  # Should be None
    print(f"Bar after tick3: {bar3}")  # Should be None
    print(f"Bar after tick4: {bar4}")  # Should be a Bar object

    if bar4 is not None:
        print(f"Bar time: {bar4.time}")
        print(f"Open: {bar4.open}, High: {bar4.high}, Low: {bar4.low}, Close: {bar4.close}, Volume: {bar4.volume}")
        # Check values
        expected_open = (1.1000 + 1.1002) / 2  # mid of first tick
        expected_high = max((1.1000+1.1002)/2, (1.1005+1.1007)/2, (1.1003+1.1005)/2)  # max(1.1001, 1.1006, 1.1004) = 1.1006
        expected_low = min((1.1000+1.1002)/2, (1.1005+1.1007)/2, (1.1003+1.1005)/2)  # min(1.1001, 1.1006, 1.1004) = 1.1001
        expected_close = (1.1003+1.1005)/2  # 1.1004
        expected_volume = 10+15+7  # 32

        print(f"Expected: O={expected_open}, H={expected_high}, L={expected_low}, C={expected_close}, V={expected_volume}")

        # Allow small floating point differences
        assert abs(bar4.open - expected_open) < 0.0001
        assert abs(bar4.high - expected_high) < 0.0001
        assert abs(bar4.low - expected_low) < 0.0001
        assert abs(bar4.close - expected_close) < 0.0001
        assert bar4.volume == expected_volume
        print("DataEngine test passed!")
    else:
        print("DataEngine test failed: no bar generated")
        return False

    # Test flush
    bar5 = engine.flush()
    print(f"Flushed bar: {bar5}")  # Should be None because buffer is empty after processing tick4

    # Now test with another set of ticks to see if flush works
    engine2 = DataEngine("GBPUSD")
    tick5 = {
        'time': base_time,
        'bid': 1.2000,
        'ask': 1.2002,
        'volume': 5
    }
    tick6 = {
        'time': base_time + timedelta(seconds=20),
        'bid': 1.2001,
        'ask': 1.2003,
        'volume': 8
    }
    # No tick to trigger minute completion, so we call flush
    engine2.process_tick(tick5)
    engine2.process_tick(tick6)
    bar_flush = engine2.flush()
    print(f"Flushed bar from engine2: {bar_flush}")
    if bar_flush is not None:
        print(f"Flushed bar time: {bar_flush.time}")
        print(f"Flushed bar O:{bar_flush.open} H:{bar_flush.high} L:{bar_flush.low} C:{bar_flush.close} V:{bar_flush.volume}")
        print("Flush test passed!")
    else:
        print("Flush test failed: no bar generated")
        return False

    return True

if __name__ == "__main__":
    test_data_engine()