# CAMS / KFintech consolidated account statement (CAS)

## Source and parser
Mutual fund holdings across all fund houses, from the CAMS/KFintech consolidated account statement. Parser
`portfolio/cas`, extra `cas` (it uses casparser).

## Official site
<https://www.camsonline.com/> (Investors → Statements → CAS – CAMS+KFintech) or <https://mfs.kfintech.com/>.

## How the file arrives
Requested on the site; the PDF arrives as an email attachment.

## What to pick
The detailed statement, for the period you need (for example from the earliest date to today).

## Password
The password you choose when you request the statement. Pass it as `parse(path, password=...)`.

## What you get
`parse(path, owners=None, password=None) -> list[Holding]`: one holding per scheme, valued at the statement's
valuation date. A fully redeemed scheme is kept with units 0 and value 0, so a later snapshot shows the folio at zero.
`owners={"own": [scheme-name substrings], "default": "<label>"}` sets each holding's `owner`: a scheme whose name
contains any of the substrings (case-insensitive) is `"own"`, and every other scheme gets the default. Without
`owners`, every scheme is `"own"`.

## Assumptions and quirks
- casparser does the PDF reading; `holdings_from_cas(data, owners)` converts its dict, which is what the tests use.
- Values are in INR, as the statement reports them.
