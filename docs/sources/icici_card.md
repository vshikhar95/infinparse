# ICICI Bank credit card (CSV)

## Source and parser
ICICI Bank credit cards, CSV export. Parser `importers/icici_card`, base install.

## Official site
<https://www.icicibank.com/>. In internet banking: Cards → Credit card → Statements / Transactions → download as CSV.

## How the file arrives
Portal download, named like `CreditCardStatement<...>.CSV`.

## What to pick
CSV, one statement period per file.

## Password
None; the CSV is not encrypted.

## What you get
`list[Txn]` sorted by date. `amount` is signed for the card account: − charge, + payment or refund. Each row's
`notes` names the (masked) card in the section it came from, so add-on card spend is visible. `meta()` returns
`{"acct4": ...}`, the last 4 digits of the `Accountno:` line, an account number ICICI prints for the card.

## Assumptions and quirks
- Two known variants share one header: `dd/mm/yyyy` dates with a separate `CR` sign column, and `dd-Mon-yy` dates
  with signed amounts. Both are handled.
- Add-on cards appear as section lines holding a masked card number; rows below belong to that card.
- Every transaction line must have exactly 7 fields; anything else raises `ValueError`.
- The same rows also appear in the PDF statement (`icici_card_pdf`); if you load both, dedupe on date + amount.
