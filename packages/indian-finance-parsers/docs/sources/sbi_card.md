# SBI Card

## Source and parser
SBI Card credit cards, transaction-history PDF. Parser `importers/sbi_card`, base install.

## Official site
<https://www.sbicard.com/>. After logging in, open the transaction history and download it as PDF. This is not the
monthly statement PDF (View Statement), which this parser doesn't read.

## How the file arrives
Portal download, named `Transaction_history.pdf`.

## What to pick
The longest range offered. SBI Card keeps 24 months online, so download at least once every two years to keep a
gapless history.

## Password
None for the transaction-history download.

## What you get
`list[Txn]` sorted by date (the PDF is newest first); − debit, + credit. `meta()` returns `{}`.

## Assumptions and quirks
- Columns sit at fixed x positions (Date | Description | Type | Amount). If SBI Card changes the layout, adjust
  `DESC_X`, `TYPE_X` and `AMOUNT_X` in the module.
- Wrapped descriptions spill above and below their row, so each fragment is assigned to the nearest dated row.
- Zero-amount memo rows (for example notes about EMI instalments) are skipped.
- A type other than `Debit` or `Credit` raises `ValueError`.
- The transaction-history PDF prints no totals or balances, so the rows can't be reconciled against the file. A
  dropped row can't be detected here; the bank's monthly statement is the stronger source if you need that.
