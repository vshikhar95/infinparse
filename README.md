# infinparse

Parsers for personal finance data, as independent Python packages. Each one turns files you already have (statement
PDFs, Excel or CSV exports, saved pages, receipt emails) into plain dataclasses, checks them against the file's own
totals where it can, and never goes online.

| Package | What it parses | Install |
|---|---|---|
| [indian-finance-parsers](packages/indian-finance-parsers/) | Indian banks, credit cards, Zerodha, mutual-fund CAS, PPF, gold bonds, FDs | `pip install "indian-finance-parsers[all]"` |
| [purchase-history-parsers](packages/purchase-history-parsers/) | Store purchase histories: Steam, Google Play, Humble Bundle, Amazon, PlayStation (any currency) | `pip install purchase-history-parsers` |

Each package has its own README, runbooks for every source, and changelog. Install only what you need.

## Development

One [uv](https://docs.astral.sh/uv/) workspace for both packages:

```bash
uv sync
uv run pytest -q -W error
scripts/pii_check.sh            # the PII gate CI runs; pass a private denylist file as an argument locally
```

Test fixtures are synthetic. Never commit a real statement, not even a redacted one; see each package's guide for
writing fixtures.

## Licence

MIT. See [LICENSE](LICENSE).
