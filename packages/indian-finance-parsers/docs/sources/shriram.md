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
`parse(path) -> list[Holding]`: one holding per deposit, as the receipt states it: dated at the deposit date, valued at
the deposit amount, `account` = the deposit number, `matures` = the maturity date, `nominee` = the nominee as printed
(`"NA"` when the receipt says none). The name carries the rate and the
maturity amount. Whether a deposit has matured, and what it is worth today, is your judgement.

Optional: `deposits(path) -> list[Deposit]`, the receipt's terms as printed: deposit number, deposit date and amount,
rate (% p.a.), tenure in months, maturity date and amount, scheme (`"Cumulative"`), interest payout
(`"Payable on Maturity"`, `""` if not printed) and nominee. The terms are checked against each other: maturity after
the deposit date, the maturity date within 3 days of the deposit date plus the printed tenure, and a cumulative scheme paying out more than
was deposited. A failure raises `ValueError` naming the file and field. `parse()` is unaffected.

## Assumptions and quirks
- Dates are `dd-mm-yyyy`; amounts are INR.
- Missing deposit number, dates or amount raises `ValueError`.
