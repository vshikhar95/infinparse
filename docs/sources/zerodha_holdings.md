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
quantities; value = units × previous closing price. `account` is the Client ID printed in the sheet's preamble ("" if
absent). The export carries no valuation date, so `as_of` defaults to the file's modification date; pass the date you
downloaded it if that differs.

## Assumptions and quirks
- The sheet has preamble rows; the header is the row containing `Symbol` and `ISIN`, and rows end at the first blank
  `Symbol`.
