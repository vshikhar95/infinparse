# Google Play order history

## Source and parser
Google Play purchases (apps, games, subscriptions). Parser `google_play` (`purchase_history_parsers.google_play`), no extras.

## Official site
<https://play.google.com/>. Profile → Payments & subscriptions → Budget & order history.

## How the file arrives
Run the exporter [`exporters/google_play.user.js`](../../exporters/google_play.user.js) on the order-history page while
logged in (as a userscript, or pasted into the browser console). It loads the whole history, then saves the page as
`Order history - Google Play.html`. Saving the page by hand after scrolling to the end works too.

## What to pick
The full order history page.

## Password
None.

## What you get
`list[Purchase]` in INR, with `refunded=True` and `raw_type="Refunded"` for refunded orders. The page has no order
ids, so `order_id` is a hash of date + title + amount + occurrence number. Re-saving the page gives the same ids,
and repeated renewals stay distinct.

## Assumptions and quirks
- English locale: dates like `1 Oct 2026` or `19 Sept 2026`, and amounts with `₹`.
- Status words (`Refunded`, `Cancelled`, `Pending`, `Declined`) sit between the title and the date.
