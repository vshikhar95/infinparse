# SBI savings account

## Source and parser
State Bank of India savings account. Parser `importers/sbi_bank`, extras `excel` and `decrypt`.

## Official site
<https://onlinesbi.sbi/>. In internet banking: My Accounts & Profile → Account Statement → choose the period →
download as Excel.

## How the file arrives
Portal download, named `AccountStatement_<...>.xlsx`.

## What to pick
Excel format. Exports seen so far stop at 2,000 transactions each, so download a long history as several shorter
periods.

## Password
The Excel file is password-protected; the download screen states the convention. Decrypt with
`indian_finance_parsers.decrypt.decrypted(path, password)` (in memory; nothing is written to disk).

## What you get
`list[Txn]` oldest first, with `balance_after` on every row; + credit, − debit. `meta()` returns `{}`.

## Assumptions and quirks
- The header row is found by its `Date` and `Balance` cells, with columns `Date | Details | Ref No/Cheque No |
  Debit | Credit | Balance`.
- Several date formats are accepted (`dd/mm/yyyy`, `dd-mm-yyyy`, `dd Mon yyyy`, ISO).
- Wrapped details (a row with only the Details cell) are appended to the previous row.
- The parser counts dated rows and raises `ValueError` if any were skipped before the footer, and checks that every
  running balance chains from the one before it.
- When the export has its **Statement Summary** footer (Brought Forward, Dr/Cr Count, Total Debits/Credits, Closing
  Balance), the rows must match it: totals, row counts, and the balances at both ends. That catches a dropped first or
  last row, which the balance chain alone can't.
