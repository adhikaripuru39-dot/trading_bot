import pytest
import os
import csv
from datetime import datetime
from monitor import Monitor

@pytest.fixture
def monitor():
    config = {'logging': {'file': 'logs/test_bot.log', 'level': 'INFO'}}
    m = Monitor(config)
    yield m
    # cleanup
    if os.path.exists(m.log_file):
        os.remove(m.log_file)
    if os.path.exists(m.trade_log_file):
        os.remove(m.trade_log_file)
    if os.path.exists(m.log_file.parent):
        os.rmdir(m.log_file.parent)

def test_csv_sanitization(monitor):
    assert monitor._sanitize_csv_field("=cmd|' /C calc'!A0") == "'=cmd|' /C calc'!A0"
    assert monitor._sanitize_csv_field("+1-123-456-7890") == "'+1-123-456-7890"
    assert monitor._sanitize_csv_field("-150.50") == "-150.50"
    assert monitor._sanitize_csv_field("@something") == "'@something"
    assert monitor._sanitize_csv_field("normal string") == "normal string"

def test_log_trade_csv_injection(monitor):
    # Ensure fresh log file
    if os.path.exists(monitor.trade_log_file):
        os.remove(monitor.trade_log_file)
    monitor._init_trade_log()

    # Log a trade with a malicious comment
    monitor.log_trade(
        symbol="EURUSD",
        signal="BUY",
        lot_size=1.0,
        entry_price=1.1,
        stop_loss=1.0,
        take_profit=1.2,
        order_id=123,
        status="CLOSED",
        pnl=100.0,
        comment="=cmd|' /C calc'!A0"
    )

    # Read the CSV and verify it's sanitized
    with open(monitor.trade_log_file, 'r') as f:
        reader = csv.reader(f)
        headers = next(reader)
        row = next(reader)
        # comment is the last field
        assert row[-1] == "'=cmd|' /C calc'!A0"
        # ensure other fields are correctly formatted
        assert row[1] == "EURUSD"
        assert row[2] == "BUY"
        assert row[3] == "1.0"
