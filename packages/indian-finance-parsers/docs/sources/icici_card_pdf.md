# ICICI Bank credit card (PDF statement)

## Source and parser
ICICI Bank credit cards, monthly PDF statement. Parser `importers/icici_card_pdf`, base install
(plus `decrypt` to open the password-protected PDF).

## Official site
<https://www.icicibank.com/>. Statements are also in Net Banking (Credit Cards → View Statement → Download PDF) and
in the iMobile app (Cards & Forex → Manage → Statements).

## How the file arrives
Monthly email attachment from the bank's credit card statements email. The filename names the card product:
`<card>_<n>_Retail_<Product>_NORM.pdf`. Other attachments, such as EMI conversion schedules, are not statements.

## What to pick
The `_NORM.pdf` statement attachment.

## Password
Protected; the statement email and ICICI's credit-card statement help page state the convention. Decrypt with
`indian_finance_parsers.decrypt.decrypted(path, password)` (in memory; nothing is written to disk).

## What you get
`list[Txn]` sorted by date; − charge, + credit (rows ending `CR`). `notes` names the add-on card for rows under an
add-on section; `ref` is the row's `SerNo` (8 or more digits). `meta()` returns `{"product": ...}` from the filename, so each card product can map to its own account.

Optional: `summary(path) -> CardSummary`, the statement's header figures: statement and due dates ("Month dd, yyyy"),
total and minimum due, the summary row (previous balance, purchases, cash advances, payments), the four limits
(credit limit, available credit, cash limit, available cash) and, when printed, the "Statement period". A figure
followed by a separate `CR` word is a credit balance and comes back negative (previous balance and total due can
both carry it). The summary row must give the total due: previous + purchases + cash advances − payments, within
₹1. ICICI prints no finance-charges figure, so `charges` is `None` and the cash advances are in `cash_advances`.
A missing figure, a row that doesn't add up, a minimum above the total, available above the limit or a due date
before the statement date raises `ValueError` naming the file and field. `parse()` is unaffected.

## Assumptions and quirks
- Rows look like `dd/mm/yyyy <ref> <description> [reward points] [foreign amount + currency] <INR amount>[ CR]`.
- Newer statements put an offers panel beside the table; the page is cropped to the table, starting at its
  `Date SerNo.` header.
- The rows are checked against the statement summary (purchases + cash advances, payments + credits) and raise
  `ValueError` if they don't add up.
