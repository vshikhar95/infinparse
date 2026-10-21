# Sovereign Gold Bond (RBI certificate)

## Source and parser
Sovereign Gold Bonds held in RBI/bank form (not in demat). Parser `portfolio/sgb`, base install.

## Official site
<https://www.rbi.org.in/>, which issues the bonds. The certificate comes from the bank or post office you bought
through. The revaluation rate comes from <https://ibjarates.com/>.

## How the file arrives
The holding certificate PDF, usually emailed by the bank or downloadable from its internet banking after allotment.

## What to pick
The RBI certificate. A bank's own copy of the same bond is not parsed.

## Password
Usually none. If protected, follow the issuing bank's convention and decrypt first.

## What you get
`parse(path, owner="unconfirmed") -> list[Holding]`: one holding at cost (units in grams × issue price), dated at
settlement, named with the series and maturity date.
`fetch_rate() -> Decimal` gets the IBJA 999 gold rate per gram, which is the basis RBI redeems at.
`revalue(holding, rate, today)` returns a copy dated `today` at that rate.

## Assumptions and quirks
- `fetch_rate()` is the only network call in this package, and you must call it yourself; `parse()` never does.
  It sends a User-Agent naming this package.
- IBJA publishes per 10 g, AM then PM; the PM rate is preferred once it is out.
- Text labels such as `Security Code`, `Settlement Date`, `Number of Units`, `Issue Price` and `Maturity Date` must
  be present, or `ValueError` is raised.
