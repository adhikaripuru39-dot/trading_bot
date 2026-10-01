import pytest
from monitor import Monitor

def test_csv_sanitization():
    # Setup dummy monitor
    m = Monitor({'logging': {'level': 'INFO', 'file': 'logs/test.log'}})

    # Test cases
    assert m._sanitize_csv_field("=1+2") == "'=1+2"
    assert m._sanitize_csv_field("-150.50") == "-150.50"
    assert m._sanitize_csv_field("+150") == "+150"
    assert m._sanitize_csv_field("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert m._sanitize_csv_field("-cmd|' /C calc'!A0") == "'-cmd|' /C calc'!A0"
    assert m._sanitize_csv_field("Normal text") == "Normal text"

    # Pure floats and ints should be unchanged if they were strings
    assert m._sanitize_csv_field("10.5") == "10.5"
    assert m._sanitize_csv_field("-10.5") == "-10.5"

    # Test actual numerical input
    assert m._sanitize_csv_field(10.5) == 10.5
    assert m._sanitize_csv_field(-10.5) == -10.5
