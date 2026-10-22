"""SBI PPF: the YONO/netbanking transaction table, saved as a page whose table markup is escaped text.
Columns: Date | Description | Amount(₹) | Balance(₹), newest first. The amount's sign is only an icon, so each row's
sign comes from the balance change, and every row must chain.
PPF interest is credited on 31 March and worded like a deposit, so 31 Mar credits get the note "PPF interest"
for categorisation rules to match on. Not 1 Apr: deposits are commonly made that day."""
import html
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from bs4 import BeautifulSoup

from indian_finance_parsers.models import Txn


def _cells(row):
    return [re.sub(r"\s+", " ", td.get_text(" ")).strip() for td in row.find_all("td")]


def _money(s):
    return Decimal(re.sub(r"[^\d.]", "", s))


def parse(path) -> list[Txn]:
    """Oldest first, with balance_after. The first row is taken as money in."""
    page = html.unescape(Path(path).read_text(encoding="utf-8", errors="replace"))
    cells = [c for c in (_cells(r) for r in BeautifulSoup(page, "html.parser").find_all("tr")) if len(c) == 4]
    raw = [(datetime.strptime(d, "%d/%m/%Y").date(), desc, _money(a), _money(b)) for d, desc, a, b in cells]
    if not raw:
        raise ValueError(f"{Path(path).name}: no PPF transaction rows found")
    raw = sorted(reversed(raw), key=lambda t: t[0])  # oldest first, keeping same-day page order
    signed = [raw[0]]
    for row, ((_, _, _, prev), (d, desc, amount, bal)) in enumerate(zip(raw, raw[1:]), start=2):
        if abs(bal - prev) != amount:
            raise ValueError(f"{Path(path).name}: PPF balance doesn't chain at row {row} (oldest first)")
        signed.append((d, desc, amount if bal >= prev else -amount, bal))
    return [Txn(date=d, amount=a, description=desc, balance_after=b,
                notes="PPF interest" if a > 0 and (d.month, d.day) == (3, 31) else "")
            for d, desc, a, b in signed]


def meta(path):
    return {}
