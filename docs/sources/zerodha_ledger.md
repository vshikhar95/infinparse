# Zerodha funds ledger

## Source and parser
Zerodha trading account funds ledger, CSV. Parser `importers/zerodha_ledger` (it re-exports
`portfolio.zerodha.ledger`), base install.

## Official site
<https://console.zerodha.com/>. Funds → Statement → choose a date range → download CSV (XLSX is also offered;
the parser reads the CSV).

## How the file arrives
Portal download, named `ledger-<client id>-<fy>.csv`.

## What to pick
CSV, one date range per file (a financial year is a convenient unit). Files may overlap; dedupe when combining.

## Password
None.

## What you get
`list[Txn]` with `balance_after`: + credit (funds added, sale proceeds), − debit. The opening and closing balance rows
are not returned. `meta()` returns `{}`.

## Assumptions and quirks
- Columns: `particulars, posting_date, cost_center, voucher_type, debit, credit, net_balance`; dates are ISO.
- The first row is `Opening Balance` (net balance only). If a trailing `Closing Balance` row exists, it must equal
  the last row's balance, and every row's balance must chain from the one before it; otherwise `ValueError` is raised.
- `portfolio.zerodha.opening(path)` and `closing(path)` expose those two balances.
