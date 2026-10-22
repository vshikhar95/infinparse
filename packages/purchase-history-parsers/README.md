# purchase-history-parsers

Parse store purchase histories into plain Python records: what you bought, when, for how much, and how you paid,
going as far back as each store's own history.

Part of [infinparse](../../README.md). Each parser takes one file you exported from your own account and returns a
list of `Purchase` dataclasses. No parser logs in or makes network calls. For stores with no export button, the
[browser exporters](exporters/) produce the file from your own logged-in browser session.

## Supported stores

| Store | File you need | How to get it | Parser | Runbook |
|---|---|---|---|---|
| Steam | purchase-history page, saved as HTML | [exporter](exporters/steam.user.js) | `steam` | [docs/sources/steam.md](docs/sources/steam.md) |
| Google Play | order-history page, saved as HTML | [exporter](exporters/google_play.user.js) | `google_play` | [docs/sources/google_play.md](docs/sources/google_play.md) |
| Humble Bundle | `humble_orders.json` | [exporter](exporters/humble.user.js) | `humble` | [docs/sources/humble.md](docs/sources/humble.md) |
| Amazon | `Your Orders.zip` | Amazon's data request | `amazon` | [docs/sources/amazon.md](docs/sources/amazon.md) |
| PlayStation Store | receipt email saved as `.html` | your mail client | `playstation` | [docs/sources/playstation.md](docs/sources/playstation.md) |

Any currency works; each row keeps the currency the store shows. Some parsers expect English-language pages; see each
runbook.

## Install and use

```bash
pip install purchase-history-parsers
```

No dependencies beyond the standard library.

```python
from purchase_history_parsers import parser

rows = parser("steam").parse("steam-account.html")   # list[Purchase]
```

`parser("mypkg.mystore")` loads your own parser by dotted path, so you don't need a fork.

## Exporters

The exporters are small JavaScript files that run in **your** browser, on the store's own page, while you're logged in.
Each loads your full history and downloads the file the matching parser reads. Install one in a userscript manager
(Tampermonkey, Violentmonkey) to get an "Export" button on the page, or paste it into the browser's developer console
to run it once. Your password never touches this package, and the Python parsers never go online.

## The model

**`Purchase`**

| Field | Type | Meaning |
|---|---|---|
| `store` | `str` | `steam`, `amazon`, ... |
| `order_id` | `str` | the store's id (or a stable hash when the store shows none) |
| `date` | `date` | order date |
| `items` | `str` | item names joined with ` \| ` |
| `kind` | `str` | `purchase`, `refund`, `market` or `other` |
| `amount` | `Decimal` | + spent, − returned, in `currency` |
| `currency` | `str` | `INR`, `USD`, ... |
| `payment` | `str` | payment method as the store shows it |
| `original_amount` | `Decimal \| None` | pre-discount price, if shown |
| `charged` | `Decimal \| None` | part paid from a real account (0 if store credit paid it all; `None` = all of `amount`) |
| `refunded` | `bool` | the store marks the order refunded |
| `raw_type` | `str` | the store's own type or status text |

## Licence

MIT. See [LICENSE](LICENSE).
