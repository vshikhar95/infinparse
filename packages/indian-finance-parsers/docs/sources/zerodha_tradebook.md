# Zerodha tradebook

## Source and parser
Zerodha equity trades. Parser `trades/zerodha_tradebook`, base install.

## Official site
<https://console.zerodha.com/>. Reports → Tradebook → choose the equity segment and a date range (Console limits each
download to a year) → download CSV.

## How the file arrives
Portal download: `tradebook-<client id>-EQ-<period>.csv`.

## What to pick
Equity segment, up to a year per file. Ranges may overlap; dedupe on `trade_id` + `exchange`.

## Password
None.

## What you get
`parse(path) -> list[Trade]`, one per executed trade, with `side` `buy` or `sell`, quantity, price and exchange.

## Assumptions and quirks
- Columns: `symbol, isin, trade_date, exchange, segment, series, trade_type, auction, quantity, price, trade_id,
  order_id, order_execution_time`; dates are ISO.
- A `trade_type` other than `buy`/`sell` raises `ValueError`.
