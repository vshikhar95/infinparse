# Amazon order history

## Source and parser
Amazon orders and refunds, from Amazon's personal-data export. Parser `amazon` (`purchase_history_parsers.amazon`), no extras.

## Official site
<https://www.amazon.in/>. Account → Request your data (under privacy / data requests) → Your Orders.

## How the file arrives
Amazon emails a download link when the export is ready. Keep `Your Orders.zip` as is; it is read in place.

## What to pick
The "Your Orders" category. It covers all marketplaces from the account's first order.

## Password
None.

## What you get
`list[Purchase]`: one purchase per order id, with item rows summed and cancelled items dropped; plus one negative
`refund` row per completed refund (`order_id` `refund:<order id>:<n>`). Orders paid fully by gift card have
`charged=0`. Address and gift-message columns are never read.

## Assumptions and quirks
- Reads `Your Amazon Orders/Order History.csv` and `Your Returns & Refunds/Refund Details.csv` inside the zip.
- Digital content orders (for example Kindle) are not included.
- The currency comes from each row, so non-INR marketplaces keep their own currency.
