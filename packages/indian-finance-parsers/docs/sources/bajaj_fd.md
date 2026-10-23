# Bajaj Finance fixed deposit

## Source and parser
Bajaj Finance fixed deposits, deposit receipt PDFs. Parser `portfolio/bajaj_fd`, base install.

## Official site
<https://www.bajajfinserv.in/>. Receipts are also available from the customer portal's fixed deposit section.

## How the file arrives
An email attachment when a deposit is opened or renewed, or a portal download.

## What to pick
One receipt per deposit, for open and closed deposits alike.

## Password
Some receipts are protected, with the convention stated in the email. Decrypt first if needed.

## What you get
`parse(path) -> list[Holding]`: one holding per deposit, as the receipt states it: dated at the deposit date, valued at
the deposit amount, `account`/`isin` = the deposit number, `matures` = the maturity date, `nominee` = the filled
nominee slots `; `-joined (`""` when none are filled, `"NA"` when the receipt says none). The name carries the rate and
the maturity amount. Whether a deposit has matured, and what it is worth today, is your judgement.

`deposits(path) -> list[Deposit]` returns the terms as printed: rate, tenure in months, scheme (`Cumulative`),
interest payout (as printed) and maturity amount.

## Assumptions and quirks
- Dates are `dd-mm-yyyy`; amounts are INR. The deposit period prints as `<months>M <days>D`; only the months are kept.
- The deposit amount plus the interest amount must equal the maturity amount (within ₹1), the maturity must be after
  the deposit date, and the tenure must match the two dates within a month; otherwise `ValueError` names the file and
  field, never amounts.
- Text without `Bajaj Finance` and the `DEPOSIT NUMBER:` header, or without the deposit row, raises `ValueError`.
- The interest payout line (`Interest Payment <label> : <value>`) and the `Nominee n :` slots are optional.
