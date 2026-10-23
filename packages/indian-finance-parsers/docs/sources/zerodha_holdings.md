# Zerodha holdings

## Source and parser
Zerodha demat holdings. Parser `portfolio/zerodha_holdings`, extra `excel`.

## Official site
<https://console.zerodha.com/>. Portfolio → Holdings → download XLSX.

## How the file arrives
Portal download: `holdings-<client id>.xlsx`.

## What to pick
The current snapshot.

## Password
None.

## What you get
`parse(path, as_of=None) -> list[Holding]`, one per stock. Units = available + discrepant + pledged (margin and loan)
quantities; value = units × previous closing price; cost = units × the sheet's Average Price (`None` if that
column is missing or 0). From the sheet's preamble: `account` is the Client ID ("" if
absent) and `as_of` is the "Statement as on" date. If a file has no such date, `as_of` falls back to the argument, then
to the file's modification date.

## Assumptions and quirks
- When the preamble prints `Invested Value` and `Present Value`, the rows must match them: Σ units × Average Price
  and Σ units × previous close, within ₹1 (real sheets are a few paise off from rounding). A mismatch raises
  `ValueError` naming the file and field. Older exports without those labels skip the check.
- An unlisted holding (for example a 54EC bond) can have a blank ISIN cell and its ISIN as the Symbol; then, and only
  then, the Symbol (`IN` + 10 letters or digits) is used as `isin`.
- The table starts in column B, under preamble rows; the header is the row containing `Symbol` and `ISIN`, and rows end at the first blank
  `Symbol`.
