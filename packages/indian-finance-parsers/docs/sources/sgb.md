# Sovereign Gold Bond (RBI certificate)

## Source and parser
Sovereign Gold Bonds held in RBI/bank form (not in demat). Parser `portfolio/sgb`, base install.

## Official site
<https://www.rbi.org.in/>, which issues the bonds. The certificate comes from the bank or post office you bought
through.

## How the file arrives
The holding certificate PDF, usually emailed by the bank or downloadable from its internet banking after allotment.

## What to pick
The RBI certificate. A bank's own copy of the same bond is not parsed.

## Password
Usually none. If protected, follow the issuing bank's convention and decrypt first.

## What you get
`parse(path) -> list[Holding]`: one holding at cost (units in grams × issue price), dated at settlement, named with
the series, with `account`/`isin` = the security code and `matures` = the maturity date. Valuing it today is your
job: RBI redeems at the IBJA 999 gold price (<https://ibjarates.com/>).

`cost` is the certificate's Consideration Amount (what was paid; `None` if not printed), while `value` stays units ×
issue price. `nominee` is the names under "Nominee Details" (rows: serial number, then the name; words the column header lists after "Nominee Name", such as a relationship or
share, are not part of it), `; `-joined, or `""`
when the certificate has no such section or rows.

## Assumptions and quirks
- Text labels such as `Security Code`, `Settlement Date`, `Number of Units`, `Issue Price` and `Maturity Date` must
  be present, or `ValueError` is raised.
