## 2024-03-01 - CSV Injection Vulnerability in Trade Logging
**Vulnerability:** Trade logging mechanism in `monitor.py` passed unsanitized values into a CSV file. Fields like comments could be manipulated to contain `=cmd|` or similar, leading to code execution if the CSV is opened in Excel.
**Learning:** Whitespace bypasses are common, so `.lstrip()` must be applied first. Crucially, purely numeric strings like `-150.50` must be excluded from single-quote prepending, as this corrupts downstream data analytics expecting numeric values.
**Prevention:** Always implement a sanitization layer before writing untrusted data to CSVs. Ensure the sanitization correctly distinguishes between numeric types and potentially malicious strings starting with special characters (`=`, `+`, `-`, `@`).
