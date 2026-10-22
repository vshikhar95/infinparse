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
`indian_finance_parsers.decrypt.decrypted(path, password, tmpdir)`.

## What you get
`list[Txn]` sorted by date; − charge, + credit. `meta()` returns `{"bin4": ...}`, the first 4 card digits from the
filename (empty if the filename was changed), so each card can map to its own account.

## Assumptions and quirks
- Two layouts are handled: 2024 (`dd/mm/yyyy hh:mm:ss  desc  [points]  1,234.56[Cr]`) and 2025 onwards
  (`dd/mm/yyyy| hh:mm  desc  [+] ₹ 1,234.56`, where `+` marks a credit).
- Rows are rebuilt from word positions. The reward-points (NeuCoins) column is dropped by its x position, so a `+`
  in that column is not read as a credit.
- A long description can be printed on the lines above and below a dated row; it is joined back.
- A leading `EMI ` before the merchant marks a charge that is merely *eligible* for EMI conversion (the statement's
  legend says so). It's still an ordinary charge, so the marker is removed from `description` and `notes` says
  `"EMI eligible"`.
- The rows are reconciled against amounts printed in the statement, and finance charges are allowed for.
  A mismatch raises `ValueError`.
