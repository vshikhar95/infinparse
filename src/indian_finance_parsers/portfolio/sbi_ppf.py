"""SBI PPF: the YONO/netbanking transaction table, saved as a page whose table markup is escaped text.
Columns: Date | Description | Amount(₹) | Balance(₹), newest first.
The amount's sign is only an icon, so every row is checked against the balance change instead."""
import html
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from indian_finance_parsers.models import Holding


def _cells(row):
    return [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]


def _money(s):
    return Decimal(re.sub(r"[^\d.]", "", s))


def rows(path):
    """[(date, description, signed amount, balance)] oldest first. Signs come from the balance change (the page
    shows direction only as an icon); the first row is taken as money in."""
    page = html.unescape(Path(path).read_text(encoding="utf-8", errors="replace"))
    cells = [c for c in (_cells(r) for r in re.findall(r"<tr.*?</tr>", page, re.S)) if len(c) == 4]
    raw = [(datetime.strptime(d, "%d/%m/%Y").date(), desc, _money(a), _money(b)) for d, desc, a, b in cells]
    if not raw:
        raise ValueError("no PPF transaction rows found")
    raw = sorted(reversed(raw), key=lambda t: t[0])  # oldest first, keeping same-day page order
    out = [raw[0]]
    for (_, _, _, prev), (d, desc, amount, bal) in zip(raw, raw[1:]):
        if abs(bal - prev) != amount:
            raise ValueError(f"PPF balance doesn't chain on {d}: change {bal - prev}, amount {amount}")
        out.append((d, desc, amount if bal >= prev else -amount, bal))
    return out


def parse(path, owner="own", account="SBI PPF"):
    d, _, _, balance = rows(path)[-1]
    return [Holding(as_of=d, source="ppf", account=account, name=account, isin="SBI-PPF",
                    units=Decimal(1), price=balance, value=balance, owner=owner)]
