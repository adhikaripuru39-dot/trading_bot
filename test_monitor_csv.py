import pytest
import os
import csv
from pathlib import Path
from monitor import Monitor

@pytest.fixture
def temp_monitor(tmp_path):
    config = {
        'logging': {
            'level': 'INFO',
            'file': str(tmp_path / 'logs' / 'bot.log')
        }
    }
    return Monitor(config)

def test_sanitize_csv_field(temp_monitor):
    # Pure numbers should be unchanged
    assert temp_monitor._sanitize_csv_field("-150.50") == "-150.50"
    assert temp_monitor._sanitize_csv_field("150.50") == "150.50"
    assert temp_monitor._sanitize_csv_field("0") == "0"

    # Malicious inputs should be prefixed with single quote
    assert temp_monitor._sanitize_csv_field('=cmd|') == "'=cmd|"
    assert temp_monitor._sanitize_csv_field('+cmd|') == "'+cmd|"
    assert temp_monitor._sanitize_csv_field('-cmd|') == "'-cmd|"
    assert temp_monitor._sanitize_csv_field('@cmd|') == "'@cmd|"

    # Normal text should be unchanged
    assert temp_monitor._sanitize_csv_field('EURUSD') == 'EURUSD'
    assert temp_monitor._sanitize_csv_field('BUY') == 'BUY'

    # Empty and none
    assert temp_monitor._sanitize_csv_field('') == ''
    assert temp_monitor._sanitize_csv_field(None) is None

    # Numbers as numbers
    assert temp_monitor._sanitize_csv_field(150.5) == 150.5

def test_log_trade_sanitizes_csv(temp_monitor, tmp_path):
    # Log a trade with potentially malicious comment
    temp_monitor.log_trade(
        symbol="EURUSD",
        signal="BUY",
        lot_size=0.1,
        entry_price=1.1000,
        stop_loss=1.0900,
        take_profit=1.1200,
        order_id=12345,
        status="CLOSED",
        pnl=-150.50, # Numeric negative value, should NOT be sanitized
        comment="=cmd|' /C calc'!A0" # Malicious, SHOULD be sanitized
    )

    log_file = tmp_path / 'logs' / 'trades.csv'
    assert log_file.exists()

    with open(log_file, 'r') as f:
        reader = csv.reader(f)
        headers = next(reader)
        row = next(reader)

        # Check PNL (index 9) - it's passed as float but converted to str in csv
        assert row[9] == "-150.5" # -150.50 formatting may differ depending on float to str, but shouldn't have quote

        # Check Comment (index 10)
        assert row[10] == "'=cmd|' /C calc'!A0"
