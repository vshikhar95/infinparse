# indian-finance-parsers

Parse Indian bank, card, broker and store statements into plain Python records.

Each parser takes one file you downloaded or were emailed (a statement PDF, an Excel or CSV export, a saved web page,
a saved receipt email) and returns a list of dataclasses. It also checks the rows against the file's own totals or
running balances where the file has them, and raises when they don't match.

## Supported sources

| Source | File you need | How it arrives | Parser | Extra | Runbook |
|---|---|---|---|---|---|
| ICICI Bank savings | `OpTransactionHistory*.xls` | download | `importers/icici_bank` | `excel` | [docs/sources/icici_bank.md](docs/sources/icici_bank.md) |
| ICICI credit card | `CreditCardStatement*.csv` | download | `importers/icici_card` | – | [docs/sources/icici_card.md](docs/sources/icici_card.md) |
| ICICI credit card | statement PDF | monthly email | `importers/icici_card_pdf` | `decrypt` | [docs/sources/icici_card_pdf.md](docs/sources/icici_card_pdf.md) |
| HDFC credit card | statement PDF | monthly email | `importers/hdfc_card` | `decrypt` | [docs/sources/hdfc_card.md](docs/sources/hdfc_card.md) |
| SBI savings | `AccountStatement_*.xlsx` | download | `importers/sbi_bank` | `excel`, `decrypt` | [docs/sources/sbi_bank.md](docs/sources/sbi_bank.md) |
| SBI Card | `Transaction_history.pdf` | download | `importers/sbi_card` | – | [docs/sources/sbi_card.md](docs/sources/sbi_card.md) |
| SBI PPF | saved transactions page | saved page | `importers/sbi_ppf`, `portfolio/sbi_ppf` | – | [docs/sources/sbi_ppf.md](docs/sources/sbi_ppf.md) |
| Zerodha funds ledger | `ledger-*.csv` | download | `importers/zerodha_ledger` | – | [docs/sources/zerodha_ledger.md](docs/sources/zerodha_ledger.md) |
| Zerodha holdings, tradebook | `holdings-*.xlsx`, `tradebook-*.csv` | download | `portfolio/zerodha` | `excel` | [docs/sources/zerodha.md](docs/sources/zerodha.md) |
| Mutual funds (CAMS/KFintech CAS) | CAS PDF | email on request | `portfolio/cas` | `cas` | [docs/sources/cas.md](docs/sources/cas.md) |
| Sovereign Gold Bonds | RBI certificate PDF | email / download | `portfolio/sgb` | – | [docs/sources/sgb.md](docs/sources/sgb.md) |
| Shriram Finance FD | deposit receipt PDF | email / download | `portfolio/shriram` | `decrypt` | [docs/sources/shriram.md](docs/sources/shriram.md) |
| Steam | saved purchase-history page | saved page | `purchases/steam` | – | [docs/sources/steam.md](docs/sources/steam.md) |
| Google Play | saved order-history page | saved page | `purchases/google_play` | – | [docs/sources/google_play.md](docs/sources/google_play.md) |
| Humble Bundle | `humble_orders.json` | browser export | `purchases/humble` | – | [docs/sources/humble.md](docs/sources/humble.md) |
| Amazon | `Your Orders.zip` | data request | `purchases/amazon` | – | [docs/sources/amazon.md](docs/sources/amazon.md) |
| PlayStation Store | receipt email saved as `.html` | email | `purchases/playstation` | – | [docs/sources/playstation.md](docs/sources/playstation.md) |

The `decrypt` extra is needed only to open password-protected files; the parser itself reads the decrypted copy.

## Install and use

```bash
pip install "indian-finance-parsers[all]"
```

The base install needs only `pdfplumber`. The extras are `excel` (pandas, xlrd, openpyxl), `cas` (casparser),
`decrypt` (pikepdf, msoffcrypto-tool) and `all`.

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from indian_finance_parsers import adapter, meta
from indian_finance_parsers.decrypt import decrypted

hdfc = adapter("importers", "hdfc_card")
with TemporaryDirectory() as tmp:
    pdf = decrypted(Path("statement.PDF"), password="...", tmpdir=Path(tmp))  # password=None if not protected
    rows = hdfc.parse(pdf)        # list[Txn]
    info = meta(hdfc, pdf)        # {"bin4": "..."}: which card this statement is for
```

To see a file's structure without seeing its contents: `python -m indian_finance_parsers.peek FILE`.

## Models

All in `indian_finance_parsers.models`. Amounts are `Decimal`.

**`Txn`** (statement row)

| Field | Type | Meaning |
|---|---|---|
| `date` | `date` | posting date |
| `amount` | `Decimal` | + money into the account, − money out |
| `description` | `str` | narration as printed |
| `balance_after` | `Decimal \| None` | running balance, where the statement prints one (banks, not cards) |
| `notes` | `str` | extra context, for example which add-on card made a charge |

**`Purchase`** (store order)

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

**`Holding`** (portfolio snapshot row)

| Field | Type | Meaning |
|---|---|---|
| `as_of` | `date` | valuation date |
| `source` | `str` | `cas`, `zerodha`, `ppf`, `sgb`, `shriram` |
| `account` | `str` | folio, client id, bond or deposit number |
| `name`, `isin` | `str` | instrument |
| `units`, `price`, `value` | `Decimal` | quantity, unit price, units × price |
| `owner` | `str` | a label you choose, for example `"own"`, `"joint"`, `"other"` |

**`Trade`** (Zerodha tradebook row): `trade_id`, `date`, `symbol`, `isin`, `side` (`buy`/`sell`), `quantity`,
`price`, `exchange`.

## Privacy

Everything runs locally. Parsers read only the file you pass them: no network, no config files, no environment
variables. The one network helper, `portfolio.sgb.fetch_rate()` (the IBJA gold rate), runs only when you call it.
All test fixtures are synthetic, and CI runs a PII check over the tree and the full git history.

## Your own parser

Write a module with `parse(path)` (and optionally `meta(path)`) anywhere on your Python path, then use it by its
dotted path: `adapter("importers", "mypkg.mybank")`. No fork or registration is needed. To contribute one, add the
module, a synthetic fixture, a test and a runbook; see [docs/writing-an-adapter.md](docs/writing-an-adapter.md).
[examples/sources.example.toml](examples/sources.example.toml) shows one way a pipeline can map files to parsers.

## Scope

Files only, including emails you save as files. This package does not fetch mail, log into banks, or store anything.
Budgeting, ledgers and syncing to apps are left to the code that calls it.

## Licence

MIT. See [LICENSE](LICENSE).
