# Zerodha funds ledger

## Source and parser
Zerodha trading account funds ledger, CSV. Parser `importers/zerodha_ledger` (it re-exports
`portfolio.zerodha.ledger`), base install.

## Official site
<https://console.zerodha.com/>. Funds → Statement / Ledger → choose the financial year → download CSV.

## How the file arrives
Portal download, named `ledger-<client id>-<fy>.csv`.

## What to pick
CSV, one financial year per file. Files from adjacent years may overlap.

## Password
None.

## What you get
`list[Txn]` with `balance_after`: + credit (funds added, sale proceeds), − debit. The opening and closing balance rows
are not returned. `meta()` returns `{}`.

## Assumptions and quirks
- Columns: `particulars, posting_date, cost_center, voucher_type, debit, credit, net_balance`; dates are ISO.
- The first row is `Opening Balance` (net balance only). If a trailing `Closing Balance` row exists, it must equal
  the last row's balance, or `ValueError` is raised.
- `portfolio.zerodha.opening(path)` and `closing(path)` expose those two balances.
