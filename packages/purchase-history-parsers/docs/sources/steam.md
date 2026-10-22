# Steam purchase history

## Source and parser
Steam store purchases, refunds and Community Market activity. Parser `steam` (`purchase_history_parsers.steam`), no extras.

## Official site
<https://store.steampowered.com/>. Account details → Store & Purchase History → View purchase history.

## How the file arrives
Run the exporter [`exporters/steam.user.js`](../../exporters/steam.user.js) on the purchase-history page while logged
in (as a Tampermonkey/Violentmonkey userscript, or pasted into the browser console). It clicks "Load more" until the
whole history shows, then saves the page as `steam-account.html`. Saving the page by hand after loading everything
works too.

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
