# PlayStation Store receipts

## Source and parser
PlayStation Store purchases. Parser `purchases/playstation`, base install.

## Official site
<https://store.playstation.com/>. Transaction history (two years by default) is also under Account Management →
Transaction History on the PlayStation site; it doesn't replace the receipts, which carry the items and payment split.

## How the file arrives
A receipt email ("Thank You For Your Purchase") for each order. Save the email body as `.html`; most mail clients can
"Save as" or "Download message". One order per file.

## What to pick
The purchase receipts. Pre-order confirmations carry no order details; the charge later sends a normal receipt.

## Password
None.

## What you get
`list[Purchase]` with one item: order number, date, items, and the total in INR. `payment` lists the cards used
(masked) and `charged` is what they paid. ₹0 orders (for example PlayStation Plus monthly games) are kept with
`kind="other"` and `raw_type="free (likely PS Plus)"`.

## Assumptions and quirks
- Two receipt layouts are handled (`Date Purchased:` and the older `Date and time of purchase:`), with dates
  `dd/mm/yyyy`.
- A subscription's recurring-fee note is not counted as an item.
- A file that is not a receipt raises `ValueError`.
