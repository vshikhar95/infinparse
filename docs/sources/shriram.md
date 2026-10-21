# Shriram Finance fixed deposit

## Source and parser
Shriram Finance fixed deposits, deposit receipt (deposit advice) PDFs. Parser `portfolio/shriram`, base install.

## Official site
<https://www.shriramfinance.in/>. Deposit receipts are also available from its customer portal.

## How the file arrives
An email attachment when a deposit is opened or renewed, or a portal download.

## What to pick
One receipt per deposit, for open and closed deposits alike.

## Password
Some receipts are protected, with the convention stated in the email. Decrypt first if needed.

## What you get
`parse(path, owner="unconfirmed") -> list[Holding]`: one holding per deposit, at its deposit amount (accrued interest
is ignored). Once the maturity date has passed, the holding is dated at maturity with value 0. The name carries the
rate, the maturity date and the maturity amount.

## Assumptions and quirks
- Maturity is judged against today's date when the receipt is parsed; re-parse to refresh it.
- Dates are `dd-mm-yyyy`; amounts are INR.
- Missing deposit number, dates or amount raises `ValueError`.
