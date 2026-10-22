"""Zerodha Console tradebook CSV (tradebook-<client id>-EQ-<period>.csv)."""
import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from indian_finance_parsers.models import Trade


def parse(path) -> list[Trade]:
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    bad = {r["trade_type"] for r in rows} - {"buy", "sell"}
    if bad:
        raise ValueError(f"{Path(path).name}: unexpected trade_type {sorted(bad)}")
    return [Trade(r["trade_id"], date.fromisoformat(r["trade_date"]), r["symbol"], r["isin"], r["trade_type"],
                  Decimal(r["quantity"]), Decimal(r["price"]), r["exchange"]) for r in rows]
