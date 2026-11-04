## 2024-11-04 - [CRITICAL] CSV Injection Vulnerability in Monitor Logging
**Vulnerability:** Unsanitized string fields (like `comment`) in CSV trade logs allowed potential CSV Injection (Formula Injection) attacks if values started with '=', '+', '-', or '@'.
**Learning:** Even internal logging systems can be vectors for injection if the outputs (like CSVs) are consumed by tools like Excel or Google Sheets, which execute formulas automatically.
**Prevention:** Sanitize all fields going into CSV files by prepending a single quote (`'`) to values starting with formula triggering characters, explicitly ignoring purely numeric strings to preserve downstream calculations.
