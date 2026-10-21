# Google Play order history

## Source and parser
Google Play purchases (apps, games, subscriptions). Parser `purchases/google_play`, base install.

## Official site
<https://play.google.com/>. Profile → Payments & subscriptions → Budget & order history.

## How the file arrives
Save the order history page from your browser as HTML, after scrolling until the whole history has loaded.

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
