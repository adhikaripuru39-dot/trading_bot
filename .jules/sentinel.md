## 2024-05-18 - [CSV Injection Vulnerability in Trade Log]
**Vulnerability:** The trade logging function in `monitor.py` writes user-controlled or dynamically generated strings (like the symbol or comment field) directly to a CSV without sanitizing fields that start with executable formula characters (`=`, `+`, `-`, `@`).
**Learning:** Even internal logs like trading records can be opened in Excel, leading to unintended command execution if a field begins with formula identifiers (e.g. `=cmd(...)`).
**Prevention:** Always sanitize string inputs written to CSVs by prepending a single quote (`'`) to values starting with `=`, `+`, `-`, or `@`. Purely numerical strings should be exempt to maintain downstream data integrity.
