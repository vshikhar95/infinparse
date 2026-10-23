# HDFC Bank credit card

## Source and parser
HDFC Bank credit cards, monthly PDF statement. Parser `importers/hdfc_card`, base install
(plus `decrypt` to open the password-protected PDF).

## Official site
<https://www.hdfcbank.com/>. Past statements are also in NetBanking, in the Cards section's statement view.

## How the file arrives
Monthly email attachment from the bank's card statements email. Filenames look like
`NNNNXXXXXXXXXXNN_DD-MM-YYYY.PDF` (masked card number + statement date).

## What to pick
The statement PDF as attached; keep the original filename, because `meta()` reads it.

## Password
Protected; the statement email states the convention. Decrypt with
`indian_finance_parsers.decrypt.decrypted(path, password)` (in memory; nothing is written to disk).

## What you get
`list[Txn]` sorted by date; − charge, + credit. `meta()` returns `{"bin4": ...}`, the first 4 card digits from the
filename (empty if the filename was changed), so each card can map to its own account.

Optional: `summary(path) -> CardSummary`, the statement's header figures: statement and due dates, total and minimum
due, the summary box (previous balance, payments, purchases, finance charges), credit limit, available credit and
available cash. The 2025+ layout also gives the billing period. Neither layout prints the cash limit itself
(`cash_limit` is `None`). Figures are read by position under their labels; a missing one, a box that doesn't add up,
a minimum above the total, available above the limit or a due date before the statement date raises `ValueError`
naming the file and field. `parse()` is unaffected.

## Assumptions and quirks
- Two layouts are handled: 2024 (`dd/mm/yyyy hh:mm:ss  desc  [points]  1,234.56[Cr]`) and 2025 onwards
  (`dd/mm/yyyy| hh:mm  desc  [+] ₹ 1,234.56`, where `+` marks a credit).
- Rows are rebuilt from word positions. The reward-points (NeuCoins) column is dropped by its x position, so a `+`
  in that column is not read as a credit.
- A long description can be printed on the lines above and below a dated row; it is joined back.
- A leading `EMI ` before the merchant marks a charge that is merely *eligible* for EMI conversion (the statement's
  legend says so). It's still an ordinary charge, so the marker is removed from `description` and `notes` says
  `"EMI eligible"`.
- In the 2024 layout, payments and refunds print no time column and end in `Cr`
  (`dd/mm/yyyy TELE TRANSFER CREDIT (Ref# …) 1,234.00Cr`); they are kept as credits. An untimed line without `Cr`
  (the header's due date, total and minimum due) is not a transaction.
- The rows must match the statement's summary box, read by position in both layouts: parsed credits equal
  Payment/Credits, and parsed debits equal Purchase/Debits (plus Finance Charges when those are printed as rows). The
  box itself must add up (opening − credits + debits + charges = total due, within ₹1, since HDFC rounds the total).
  A mismatch, or a statement without a readable box, raises `ValueError` naming the file and field, never amounts.
