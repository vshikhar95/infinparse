# CAMS / KFintech consolidated account statement (CAS)

## Source and parser
Mutual fund holdings across all fund houses, from the CAMS/KFintech consolidated account statement. Parser
`portfolio/cas`, extra `cas` (it uses casparser).

## Official site
<https://www.camsonline.com/> (Statements → CAS – CAMS+KFintech), <https://mfs.kfintech.com/>, or MFCentral.
AMFI explains the CAS at <https://www.amfiindia.com/>.

## How the file arrives
Requested on the site; the PDF arrives as an email attachment.

## What to pick
The detailed statement, for the period you need (for example from the earliest date to today).

## Password
The password you choose when you request the statement. Pass it as `parse(path, password=...)`.

## What you get
`parse(path, password=None) -> list[Holding]`: one holding per scheme, valued at the statement's valuation date, with
`account` = the folio number `nominee` = the scheme's nominees as printed, and `cost` = the
statement's cost value for the units held (`None` when the statement doesn't print one; some RTAs don't). A fully redeemed scheme is kept with units 0 and value 0, so a later snapshot shows the
folio at zero. A wrong password raises `ValueError` naming only the file. casparser opens the encrypted PDF itself,
so the password goes to `parse()` rather than through `decrypt`.

## Assumptions and quirks
- casparser does the PDF reading; `holdings_from_cas(data)` converts its dict.
- Values are in INR, as the statement reports them.
