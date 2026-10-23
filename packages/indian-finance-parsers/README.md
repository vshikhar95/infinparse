# indian-finance-parsers

Parse Indian bank, card, broker and fund statements into plain Python records.

Part of [infinparse](https://github.com/vshikhar95/infinparse/blob/main/README.md); store purchase histories live in its sibling package [purchase-history-parsers](https://github.com/vshikhar95/infinparse/blob/main/packages/purchase-history-parsers).

Each parser takes one file you downloaded or were emailed (a statement PDF, an Excel or CSV export, a saved web page,
a statement saved from a web page) and returns a list of dataclasses. Where a file carries its own totals, row counts or running
balances, the parser checks the rows against them and raises `ValueError` on a mismatch, so a dropped row or a
flipped sign fails loudly instead of slipping through.

## Supported sources

| Source | File you need | How it arrives | Parser | Extra | Runbook |
|---|---|---|---|---|---|
| ICICI Bank savings | `OpTransactionHistory*.xls` | download | `importers/icici_bank` | `excel` | [docs/sources/icici_bank.md](https://github.com/vshikhar95/infinparse/blob/main/packages/indian-finance-parsers/docs/sources/icici_bank.md) |
| ICICI credit card | `CreditCardStatement*.csv` | download | `importers/icici_card` | – | [docs/sources/icici_card.md](https://github.com/vshikhar95/infinparse/blob/main/packages/indian-finance-parsers/docs/sources/icici_card.md) |
| ICICI credit card | statement PDF | monthly email | `importers/icici_card_pdf` | `decrypt` | [docs/sources/icici_card_pdf.md](https://github.com/vshikhar95/infinparse/blob/main/packages/indian-finance-parsers/docs/sources/icici_card_pdf.md) |
| HDFC credit card | statement PDF | monthly email | `importers/hdfc_card` | `decrypt` | [docs/sources/hdfc_card.md](https://github.com/vshikhar95/infinparse/blob/main/packages/indian-finance-parsers/docs/sources/hdfc_card.md) |
| SBI savings | `AccountStatement_*.xlsx` | download | `importers/sbi_bank` | `excel`, `decrypt` | [docs/sources/sbi_bank.md](https://github.com/vshikhar95/infinparse/blob/main/packages/indian-finance-parsers/docs/sources/sbi_bank.md) |
| SBI Card | `Transaction_history.pdf` | download | `importers/sbi_card` | – | [docs/sources/sbi_card.md](https://github.com/vshikhar95/infinparse/blob/main/packages/indian-finance-parsers/docs/sources/sbi_card.md) |
| SBI PPF | saved transactions page | saved page | `importers/sbi_ppf`, `portfolio/sbi_ppf` | – | [docs/sources/sbi_ppf.md](https://github.com/vshikhar95/infinparse/blob/main/packages/indian-finance-parsers/docs/sources/sbi_ppf.md) |
| Zerodha funds ledger | `ledger-*.csv` | download | `importers/zerodha_ledger` | – | [docs/sources/zerodha_ledger.md](https://github.com/vshikhar95/infinparse/blob/main/packages/indian-finance-parsers/docs/sources/zerodha_ledger.md) |
| Zerodha holdings | `holdings-*.xlsx` | download | `portfolio/zerodha_holdings` | `excel` | [docs/sources/zerodha_holdings.md](https://github.com/vshikhar95/infinparse/blob/main/packages/indian-finance-parsers/docs/sources/zerodha_holdings.md) |
| Zerodha tradebook | `tradebook-*.csv` | download | `trades/zerodha_tradebook` | – | [docs/sources/zerodha_tradebook.md](https://github.com/vshikhar95/infinparse/blob/main/packages/indian-finance-parsers/docs/sources/zerodha_tradebook.md) |
| Mutual funds (CAMS/KFintech CAS) | CAS PDF | email on request | `portfolio/cas` | `cas` | [docs/sources/cas.md](https://github.com/vshikhar95/infinparse/blob/main/packages/indian-finance-parsers/docs/sources/cas.md) |
| Sovereign Gold Bonds | RBI certificate PDF | email / download | `portfolio/sgb` | – | [docs/sources/sgb.md](https://github.com/vshikhar95/infinparse/blob/main/packages/indian-finance-parsers/docs/sources/sgb.md) |
| Shriram Finance FD | deposit receipt PDF | email / download | `portfolio/shriram` | `decrypt` | [docs/sources/shriram.md](https://github.com/vshikhar95/infinparse/blob/main/packages/indian-finance-parsers/docs/sources/shriram.md) |

The `decrypt` extra is needed only to open password-protected files; the parser itself reads the decrypted copy.

## Install and use

```bash
pip install "indian-finance-parsers[all]"
```

The base install needs only `pdfplumber`. The extras are `excel` (pandas, xlrd, openpyxl), `cas` (casparser),
`decrypt` (pikepdf, msoffcrypto-tool) and `all`.

```python
from indian_finance_parsers import adapter, meta
from indian_finance_parsers.decrypt import decrypted

hdfc = adapter("importers", "hdfc_card")
src = decrypted("statement.PDF", password="...")  # password=None if the file isn't protected
rows = hdfc.parse(src)        # list[Txn]
info = meta(hdfc, src)        # {"bin4": "..."}: which card this statement is for
```

`decrypted()` decrypts in memory: it returns an in-memory file (named like the original) that every PDF and Excel
parser accepts, so the plaintext never touches disk. It returns the path unchanged when there's no password or the
file isn't actually encrypted. Its errors name only the file, never the full path.

For your own adapters, `indian_finance_parsers.checks` has the reconciliation helpers the built-in bank parsers use:
`check_balance_chain(rows)` (raises at the first row whose running balance doesn't chain; returns the opening balance)
and `order_by_balance(rows)` (re-orders same-day rows a bank printed out of order).

To see a file's structure without seeing its contents: `python -m indian_finance_parsers.peek FILE` (needs the
`excel` extra).

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

**`Holding`** (portfolio snapshot row)

| Field | Type | Meaning |
|---|---|---|
| `as_of` | `date` | valuation date |
| `source` | `str` | `cas`, `zerodha`, `ppf`, `sgb`, `shriram` |
| `account` | `str` | identifier the file prints (folio, client id, bond or deposit number), or `""` |
| `name`, `isin` | `str` | instrument |
| `units`, `price`, `value` | `Decimal` | quantity, unit price, units × price |
| `matures` | `date \| None` | maturity date, for deposits and bonds |
| `cost` | `Decimal \| None` | amount invested in the units held, as the document states it (CAS cost value; Zerodha average price × units); `None` if it doesn't say |
| `nominee` | `str` | nominee names as printed (`; `-joined); `"NA"` if the document says none, `""` if it doesn't say |

Whose holding it is (yours, joint, someone else's) isn't in any of these files, so it isn't a field. Subclass `Holding` in
your own code if you track it.

**`CardSummary`** (a card statement's header figures; `hdfc_card.summary(path)`, `icici_card_pdf.summary(path)`)

| Field | Type | Meaning |
|---|---|---|
| `statement_date`, `due_date` | `date` | as printed |
| `period_start`, `period_end` | `date \| None` | the billing period, where the layout prints it |
| `total_due` | `Decimal` | negative when the statement prints a credit balance |
| `minimum_due` | `Decimal` | |
| `previous_balance`, `payments`, `purchases` | `Decimal` | the summary box; `payments` is positive |
| `charges` | `Decimal \| None` | finance charges, where printed (HDFC) |
| `cash_advances` | `Decimal \| None` | where printed (ICICI) |
| `credit_limit`, `available_credit` | `Decimal` | |
| `cash_limit`, `available_cash` | `Decimal \| None` | where printed |

**`Deposit`** (a fixed deposit's terms; `shriram.deposits(path)`, `bajaj_fd.deposits(path)`)

| Field | Type | Meaning |
|---|---|---|
| `deposit_no` | `str` | as printed |
| `deposited`, `matures` | `date` | |
| `amount`, `maturity_amount` | `Decimal` | deposit amount; amount payable at maturity |
| `rate` | `Decimal \| None` | % p.a., where printed |
| `tenure_months` | `int \| None` | where printed |
| `scheme` | `str` | as printed, e.g. `Cumulative` |
| `interest_payout` | `str` | as printed, e.g. `Payable on Maturity`; `""` if not printed |
| `nominee` | `str` | same convention as `Holding.nominee` |

**`Trade`** (Zerodha tradebook row): `trade_id`, `date`, `symbol`, `isin`, `side` (`buy`/`sell`), `quantity`,
`price`, `exchange`.

## Privacy

Everything runs locally. Parsers read only the file you pass them: no network, no config files, no environment
variables. Parsers report what a file says and check it against itself; valuing holdings at today's prices, judging
whether a deposit has matured and naming accounts are left to you.
All test fixtures are synthetic, and CI runs a PII check over the tree and the full git history.

## Your own parser

Write a module with `parse(path)` (and optionally `meta(path)`) anywhere on your Python path, then use it by its
dotted path: `adapter("importers", "mypkg.mybank")`. No fork or registration is needed. To contribute one, add the
module, a synthetic fixture, a test and a runbook; see [docs/writing-an-adapter.md](https://github.com/vshikhar95/infinparse/blob/main/packages/indian-finance-parsers/docs/writing-an-adapter.md).
[examples/sources.example.toml](https://github.com/vshikhar95/infinparse/blob/main/packages/indian-finance-parsers/examples/sources.example.toml) shows one way a pipeline can map files to parsers.

## Scope

Files only, including emails you save as files. This package does not fetch mail, log into banks, or store anything.
Budgeting, ledgers and syncing to apps are left to the code that calls it.

## Related projects

[Beancount](https://github.com/beancount/beancount) users write importers on
[beangulp](https://github.com/beancount/beangulp). Indian-bank importers for it include
[dumbPy/beancount-importers-india](https://github.com/dumbPy/beancount-importers-india) (GPL-3.0) and
[prabusw/beancount-importers-india](https://github.com/prabusw/beancount-importers-india) (AGPL-3.0), which cover
banks and wallets this package doesn't yet. This package is the ledger-agnostic layer underneath: a Beancount importer
can call these parsers from its `extract()`.

## Licence

MIT. See [LICENSE](https://github.com/vshikhar95/infinparse/blob/main/packages/indian-finance-parsers/LICENSE).
