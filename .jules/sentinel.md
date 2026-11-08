## 2024-11-08 - CSV Injection in Monitor Logs
**Vulnerability:** The trade logging in `monitor.py` writes fields to a CSV without sanitization. An attacker could potentially inject malicious Excel formulas (e.g., `=cmd|' /C calc'!A0`) by crafting inputs for fields like `comment`, which, when opened in a spreadsheet program, can result in arbitrary code execution.
**Learning:** Even fields perceived as safe internal logs should have output encoding when written to formats parsed by formula-evaluating applications like CSVs in Excel.
**Prevention:** Always check fields destined for CSV. Strip leading whitespaces and prepend a single quote (`'`) to strings starting with `=`, `+`, `-`, or `@`.
