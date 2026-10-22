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
quantities; value = units × previous closing price. From the sheet's preamble: `account` is the Client ID ("" if
absent) and `as_of` is the "Statement as on" date. If a file has no such date, `as_of` falls back to the argument, then
to the file's modification date.

## Assumptions and quirks
- The table starts in column B, under preamble rows; the header is the row containing `Symbol` and `ISIN`, and rows end at the first blank
  `Symbol`.
