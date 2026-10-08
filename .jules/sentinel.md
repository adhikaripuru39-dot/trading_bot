## 2026-10-08 - CSV Injection Vulnerability in Monitor

**Vulnerability:**
The `log_trade` method in `Monitor` class logged unsanitized string values (like `symbol` or `comment`) to a CSV file (`trades.csv`). This allowed potential CSV injection vulnerabilities if an attacker could control string fields that start with `=`, `+`, `-`, or `@` (e.g., in external comments or poorly validated symbols). A user opening this CSV file in a spreadsheet program could have arbitrary commands executed.

**Learning:**
Logging user-controlled or dynamically generated strings into a CSV file is dangerous without proper sanitization. The vulnerability existed because the raw strings were written straight to the CSV. However, attempting to sanitize everything starting with `-` breaks negative numeric values (like `-150.50` for PnL), leading to data corruption and breaking automated reports that expect numeric fields.

**Prevention:**
Always sanitize string inputs before writing to CSV files when those fields could originate from external inputs. Specifically, check if the string begins with characters like `=`, `+`, `-`, or `@`. Additionally, ensure that numeric parsing logic correctly excludes valid numeric strings (e.g., negative numbers) to preserve data integrity and prevent downstream errors.
