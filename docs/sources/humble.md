# Humble Bundle orders

## Source and parser
Humble Bundle bundles, store orders and Humble Choice. Parser `purchases/humble`, base install.

## Official site
<https://www.humblebundle.com/>. Your orders are listed under your account's Purchases page.

## How the file arrives
Humble has no export button. While logged in, collect the JSON from its order API (`/api/v1/order` and
`/api/v1/order/<gamekey>`) in the browser and save it as `humble_orders.json`: a list of
`{"id", "created", "amount_spent", "total", "currency", "product", "category", "items", "is_giftee", "claimed"}`.
Store a hash of each gamekey as `id`, never the gamekey or any game keys.

## What to pick
All orders.

## Password
None.

## What you get
`list[Purchase]`: `kind` is `purchase` when money was spent and `other` for free or gifted orders (`raw_type` is
`"gift received"` for gifts). `items` is the bundle name followed by its games.

## Assumptions and quirks
- Older orders are in USD and newer ones may be INR; freebies can have no currency, which is kept as empty.
