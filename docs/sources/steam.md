# Steam purchase history

## Source and parser
Steam store purchases, refunds and Community Market activity. Parser `purchases/steam`, base install.

## Official site
<https://store.steampowered.com/>. Account details → View purchase history.

## How the file arrives
Save the purchase-history page from your browser as HTML, after clicking "Load more" until the whole history shows.

## What to pick
The full history page.

## Password
None.

## What you get
`list[Purchase]`: `kind` is `purchase`, `refund` (negative amount), `market` (negative when an item was sold into
the wallet) or `other`. `charged` is the part paid by card when the wallet covered the rest, and 0 when the wallet
paid everything. A purchase and its refund share Steam's transaction id, so `order_id` is `<transid>:<kind>`. Market
rows have no id, so theirs is a hash of the row text, which stays stable when the page is re-saved.

## Assumptions and quirks
- Currency is INR when amounts show `₹`, USD for `$`, otherwise the trailing code.
- Dates use the English format `5 Oct, 2026`.
