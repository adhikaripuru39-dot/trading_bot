## 2025-02-14 - CSV Injection Prevention in Trade Logs
**Vulnerability:** Trade logs generated in CSV format (in `monitor.py`) could potentially be vulnerable to CSV Injection if any fields (like `comment`) start with `=`, `+`, `-`, or `@`.
**Learning:** Preventing CSV injection requires care not to corrupt legitimate numerical data (e.g. negative PnL values passed as strings). Applying a blanket prefix of `'` to all strings starting with `-` or `+` breaks data pipelines.
**Prevention:** Always verify if a string that starts with a formula character is actually a valid number (e.g., using `float(value)`) before deciding to sanitize it with a `'` prefix.
