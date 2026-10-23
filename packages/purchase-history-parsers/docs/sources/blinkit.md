# Blinkit orders

## Source and parser
Blinkit grocery orders. Parser `blinkit` (`purchase_history_parsers.blinkit`), no extras.

## Official site
<https://blinkit.com/>. Your orders are listed under Account → My Orders.

## How the file arrives
Blinkit has no export button. Run the exporter [`exporters/blinkit.user.js`](../../exporters/blinkit.user.js) on
`blinkit.com/account/orders` while logged in (as a userscript, or pasted into the browser console). Click the "Export
orders" button it adds: Chrome drops downloads that a user click didn't trigger. It reads your orders from Blinkit's
own endpoints in your session, one call every ~1.5 s to stay under the rate limit, so a few hundred orders take about
10 minutes. It downloads `blinkit-orders.PERSONAL.json`. Address, phone and name are never read, and card digits are
stripped from the payment method.

## What to pick
All orders.

## Password
None.

## What you get
`list[Purchase]`: `amount` is the order's bill total (fees, tips and donation included, coupons deducted). `kind` is
`purchase` for delivered orders with a total and `other` otherwise (`raw_type` is the order status, for example
`CANCELLED`). `items` lists names, with ` ×N` when more than one was bought. `payment` is `Card`, `UPI` and so on,
never digits.

## Assumptions and quirks
- INR only.
- Orders without a date are skipped; orders without a total are kept as `other` with amount 0.
- The exporter calls Blinkit's undocumented page endpoints, so a site change can break it.
