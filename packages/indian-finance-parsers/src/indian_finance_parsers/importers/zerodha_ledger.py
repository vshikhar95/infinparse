"""Zerodha Console funds ledger CSV (ledger-<client id>-<period>.csv)."""
import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from indian_finance_parsers.checks import check_balance_chain
from indian_finance_parsers.models import Txn


def _dec(v) -> Decimal:
    return Decimal(str(v or 0).replace(",", "").strip() or 0)


def parse(path) -> list[Txn]:
    """Dated rows only. The Opening Balance row and, if present, the Closing Balance row are checked against the
    rows, not returned; every row's balance must chain."""
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    name = Path(path).name
    txns = [Txn(date.fromisoformat(r["posting_date"]), _dec(r["credit"]) - _dec(r["debit"]), r["particulars"],
                _dec(r["net_balance"]),
                notes=(r.get("voucher_type") or "").strip()) for r in rows if r["posting_date"]]
    opening = _dec(rows[0]["net_balance"]) if rows and rows[0]["particulars"] == "Opening Balance" else None
    start = check_balance_chain(txns)  # raises if the rows don't chain among themselves
    if txns and opening is not None and start != opening:
        raise ValueError(f"{name}: rows don't chain from the Opening Balance row")
    last = txns[-1].balance_after if txns else opening
    if rows and rows[-1]["particulars"] == "Closing Balance" and _dec(rows[-1]["net_balance"]) != last:
        raise ValueError(f"{name}: Closing Balance row doesn't match the last row's balance")
    return txns


def meta(path):
    return {}
