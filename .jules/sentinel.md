## 2023-11-01 - CSV Injection Vulnerability in Monitor
**Vulnerability:** The trading bot logged user/system input directly to a CSV file without sanitizing fields starting with '=', '+', '-', or '@'. This creates a CSV Injection (Formula Injection) vulnerability if the CSV file is opened in software like Excel.
**Learning:** Even internal logs like trading records require input sanitization if they are designed to be exported and viewed in spreadsheet software.
**Prevention:** Always implement a sanitization layer before writing dynamic fields to CSVs by prefixing unsafe characters with a single quote (').
