## 2024-10-02 - CSV Injection Vulnerability in Trade Monitoring
**Vulnerability:** User-controlled or dynamic fields written to `trades.csv` in `monitor.py` were not sanitized.
**Learning:** Fields starting with '=', '+', '-', or '@' can execute arbitrary formulas in spreadsheet applications like Excel, potentially leading to command execution or data exfiltration if they are opened by a user.
**Prevention:** Sanitize fields written to CSV by prepending a single quote (`'`) to values starting with '=', '+', '-', or '@' (excluding pure numeric values which are generally safe and required for data integrity).
