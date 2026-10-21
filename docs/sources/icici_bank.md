# ICICI Bank savings account

## Source and parser
ICICI Bank savings or current account. Parser `importers/icici_bank`, extra `excel`.

## Official site
<https://www.icicibank.com/>. In internet banking: Accounts → Account statement / Transaction history → choose the
period → download as XLS.

## How the file arrives
Portal download. The file is named `OpTransactionHistory<...>.xls`.

## What to pick
XLS format, any date range. For long histories, download several periods; keep each period's rows complete.

## Password
None; the XLS download is not encrypted.

## What you get
`list[Txn]` oldest first, with `balance_after` on every row. `amount` is signed: + deposit, − withdrawal.
`meta()` returns `{}`.

## Assumptions and quirks
- INR and English column headers: the header row is found by its `S No.` cell, and columns by name
  (`Transaction Date`, `Transaction Remarks`, `Withdrawal Amount(INR)`, `Deposit Amount(INR)`, `Balance(INR)`).
- Dates are `dd/mm/yyyy`.
- Long remarks wrap onto a row that has only the remarks cell; it is appended to the previous row.
- The export can be newest-first; it is reversed. Same-day rows printed out of order (a reversal before its
  payment) are re-ordered by their running balance.
- The parser counts numbered rows and raises `ValueError` if any were skipped.
