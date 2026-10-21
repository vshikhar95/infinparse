# SBI savings account

## Source and parser
State Bank of India savings account. Parser `importers/sbi_bank`, extras `excel` and `decrypt`.

## Official site
<https://onlinesbi.sbi/>. In internet banking: My Accounts & Profile → Account Statement → choose the period →
download as Excel.

## How the file arrives
Portal download, named `AccountStatement_<...>.xlsx`.

## What to pick
Excel format. One export holds at most 2,000 transactions, so a long history comes as several files.

## Password
The Excel file is password-protected; the download screen states the convention. Decrypt with
`indian_finance_parsers.decrypt.decrypted(path, password, tmpdir)`.

## What you get
`list[Txn]` oldest first, with `balance_after` on every row; + credit, − debit. `meta()` returns `{}`.

## Assumptions and quirks
- The header row is found by its `Date` and `Balance` cells, with columns `Date | Details | Ref No/Cheque No |
  Debit | Credit | Balance`.
- Several date formats are accepted (`dd/mm/yyyy`, `dd-mm-yyyy`, `dd Mon yyyy`, ISO).
- Wrapped details (a row with only the Details cell) are appended to the previous row.
- The parser counts dated rows and raises `ValueError` if any were skipped before the footer.
