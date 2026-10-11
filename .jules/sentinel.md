## 2023-10-11 - CSV Injection Vulnerability in Trade Log
**Vulnerability:** User-controlled or dynamic fields (such as comments) written to CSV files in `monitor.py` lacked sanitization. Strings starting with characters like `=`, `+`, `-`, or `@` could be interpreted as executable formulas by spreadsheet software (e.g. Excel) when the generated log file is opened.
**Learning:** Even internal logging mechanisms can become vectors for attack (CSV Injection) if the data later gets ingested by applications executing dynamic formulas.
**Prevention:** All string values written to CSV files must be sanitized by prepending a single quote (`'`) to values starting with `=`, `+`, `-`, or `@`. Purely numeric values (e.g., `-150.50`) should be exempted to preserve valid numeric formatting.
