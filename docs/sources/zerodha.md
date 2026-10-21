# Zerodha holdings and tradebook

## Source and parser
Zerodha demat holdings and trades. Module `portfolio/zerodha`: `holdings()` needs the `excel` extra; `trades()` and
`ledger()` need only the base install.

## Official site
<https://console.zerodha.com/>. Portfolio → Holdings → download XLSX; Reports → Tradebook → choose the financial
year → download CSV.

## How the file arrives
Portal downloads: `holdings-<client id>.xlsx` and `tradebook-<client id>-EQ-<fy>.csv`.

## What to pick
Holdings: the current snapshot. Tradebook: equity segment, one financial year per file (ranges may overlap; dedupe
on `trade_id` + `exchange`).

## Password
None.

## What you get
- `holdings(path, as_of=None, owner="own") -> list[Holding]`. `as_of` defaults to the file's modification date.
  Units = available + discrepant + pledged (margin and loan) quantities; value = units × previous closing price.
- `trades(path) -> list[Trade]`, with `side` `buy` or `sell`.
- `ledger(path) -> list[Txn]`: see the `zerodha_ledger` runbook.

## Assumptions and quirks
- The holdings sheet has preamble rows; the header is the row containing `Symbol` and `ISIN`, and rows end at the
  first blank `Symbol`.
- A `trade_type` other than `buy`/`sell` raises `ValueError`.
