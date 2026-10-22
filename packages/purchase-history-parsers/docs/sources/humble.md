# Humble Bundle orders

## Source and parser
Humble Bundle bundles, store orders and Humble Choice. Parser `humble` (`purchase_history_parsers.humble`), no extras.

## Official site
<https://www.humblebundle.com/>. Your orders are listed under your account's Purchases page.

## How the file arrives
Humble has no export button. Run the exporter [`exporters/humble.user.js`](../../exporters/humble.user.js) on your
Purchases page while logged in (as a userscript, or pasted into the browser console). It reads your orders from
Humble's own order endpoints in your session and downloads `humble-orders.PERSONAL.json`. Each order's gamekey (which unlocks
its games) is replaced by a hash, so the file holds no keys.

## What to pick
All orders.

## Password
None.

## What you get
`list[Purchase]`: `kind` is `purchase` when money was spent and `other` for free or gifted orders (`raw_type` is
`"gift received"` for gifts). `items` is the bundle name followed by its games.

## Assumptions and quirks
- Older orders are in USD and newer ones may be INR; freebies can have no currency, which is kept as empty.
