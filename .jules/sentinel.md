## 2024-05-18 - CSV Injection in Monitor Logging
**Vulnerability:** The trade logging mechanism in `monitor.py` was writing untrusted input to a CSV file (`trades.csv`) without sanitizing fields starting with `=`, `+`, `-`, or `@`.
**Learning:** Writing arbitrary strings to CSV files can lead to CSV Injection (Formula Injection) vulnerabilities when the CSV is opened in spreadsheet software like Excel. If a comment or other text field starts with a formula character, Excel will execute it.
**Prevention:** Sanitize all fields before writing them to CSV by checking if they start with a dangerous character and prefixing them with a single quote `\''`. Ensure that purely numeric fields (e.g. `-150.50`) are excluded from sanitization so data integrity is maintained.
