# Writing an adapter

An adapter is one Python module that turns one kind of file into records from `indian_finance_parsers.models`.

## The contract

| Kind | Function | Returns |
|---|---|---|
| Statement importer | `parse(path)`, and optionally `meta(path) -> dict[str, str]` | `list[Txn]` |
| Portfolio parser | `parse(path)` | `list[Holding]` |
| Trade parser | `parse(path)` | `list[Trade]` |

The folder an adapter lives in (`importers/`, `portfolio/`, `trades/`) decides which record it returns.
One module per document: one institution's one export (Zerodha's holdings sheet, tradebook and funds ledger are three
modules). Extra keyword arguments are for what the file itself can't supply and the parser can't do without, such as
a password the parsing library needs (`cas.parse(path, password=)`).

Optional extras: when a document carries more than `parse()` returns (a card statement's header figures, a deposit
receipt's terms), add a second entry point with its own record in `models.py`, for example `summary(path) -> CardSummary`
or `deposits(path) -> list[Deposit]`. `parse(path)` and its result stay unchanged, so existing callers never see the
extra; the same rules apply (report the document, check it against itself, errors name the file and field).

Rules:
- **Report the document, don't judge it.** Return what the file says. Checking the file against itself (totals,
  running balances, row counts) belongs here; anything that needs today's date, the network, or knowledge about the
  user (whose money it is, what the account is called, whether a deposit has matured, today's price) belongs to the
  caller.
- **Pure.** `parse()` and `meta()` read only the file they are given. No config files, environment variables,
  databases or network calls.
- **Identifiers from the file, names from the caller.** Fill `account` (or `meta()` placeholders) with identifiers the
  file prints: folio, client id, deposit number, card digits. Never invent an account name; leave `""` when the file
  has none.
- **Reconcile or raise.** If the file carries totals or running balances, check the rows against them and raise
  `ValueError` when they disagree. A parser that silently drops a row is worse than one that fails.
- **Heavy dependencies are imported inside the function** that needs them (pandas, openpyxl, casparser), so a user
  who installs only the base package can still import the other adapters.
- `meta()` returns placeholders for naming the account the rows belong to, for example `{"last4": "1234"}` or
  `{"product": "Platinum"}`. Return `{}`, or omit `meta`, if the file says nothing about which account it is.

## Using your own adapter without a fork

Put the module anywhere importable and refer to it by its dotted path:

```python
from indian_finance_parsers import adapter, meta

mod = adapter("importers", "mypkg.mybank")   # a bare name like "hdfc_card" means a built-in
rows = mod.parse("statement.csv")
info = meta(mod, "statement.csv")             # {} when the module has no meta()
```

## Contributing one upstream

1. **Add the module** under `src/indian_finance_parsers/<importers|portfolio|trades>/`.
2. **Add a synthetic fixture.** Look at your real file's structure with
   `python -m indian_finance_parsers.peek path/to/real-file.csv` (needs the `excel` extra), which prints it with every letter and digit masked.
   Then write a small fixture with that structure and invented values (shop names like `TESTMART`, card numbers
   starting `4111`, account numbers of zeros). Never commit a real statement, not even a redacted one.
   For PDFs, test the function that turns extracted words or lines into rows, and store those words or lines as JSON
   or text; see `tests/fixtures/hdfc_card_rows.json`.
3. **Add one test** that asserts the row count, the first row, and the reconciliation (and that a broken total
   raises).
4. **Add a runbook**: copy `docs/sources/_template.md` to `docs/sources/<module>.md` and fill in every heading. Then
   add a row to the README's sources table. `tests/test_docs.py` fails until both exist.
5. Run `uv run pytest -q -W error` and `scripts/pii_check.sh` before opening the pull request.
