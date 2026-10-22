# SBI PPF account

## Source and parser
State Bank of India Public Provident Fund account. Two parsers read the same saved page:
`importers/sbi_ppf` (the transactions, as a statement) and `portfolio/sbi_ppf` (the current balance, as a holding).
Base install.

## Official site
<https://onlinesbi.sbi/> or the YONO app. Open the PPF account → transactions / mini statement.

## How the file arrives
Save the transaction table page from your browser as HTML (File → Save Page As). The table markup on that page is
escaped text, which the parser reads as is.

## What to pick
The full transaction list for the account, newest first as the page shows it.

## Password
None.

## What you get
- `importers/sbi_ppf.parse(path)` → `list[Txn]` oldest first, with `balance_after`. Credits on 31 March get the note
  `"PPF interest"`, because interest is worded like a deposit. `meta()` returns `{}`.
- `portfolio/sbi_ppf.parse(path, owner="own", account="SBI PPF")` → one `Holding` with the latest balance.
- `portfolio/sbi_ppf.rows(path)` → the raw `(date, description, signed amount, balance)` tuples.

## Assumptions and quirks
- Columns: `Date | Description | Amount(₹) | Balance(₹)`, dates `dd/mm/yyyy`.
- The page shows a row's direction only as an icon, so the sign comes from the balance change. Every row must
  chain, or `ValueError` is raised. The oldest row is taken as money in.
