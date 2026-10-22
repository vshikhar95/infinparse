"""Shriram Finance FD receipts (deposit advice PDFs; some password-protected) -> one Holding per deposit, as the
receipt states it: dated at the deposit date, valued at the deposit amount, with its maturity date. Whether it has
matured, and what it is worth today, is the caller's judgement."""
import re
from datetime import datetime
from decimal import Decimal

import pdfplumber

from indian_finance_parsers.models import Holding

D8 = r"(\d\d-\d\d-\d{4})"


def _d(s):
    return datetime.strptime(s, "%d-%m-%Y").date()


def holding_from_text(text) -> Holding:
    no = re.search(r"Deposit No\. ([A-Z]+-\d+)", text)
    row = re.search(D8 + r" \d+ \*?([\d,]+\.\d\d) " + D8, text)  # deposit date, months, maturity amount, maturity date
    amount = re.search(r"Deposit Amount : ₹?([\d,]+\.\d\d)", text)
    rate = re.search(r"([\d.]+) % p\.a\.", text)
    nominee = (re.search(r"Nominee : (.+)", text) or [None, ""])[1].strip()
    if not (no and row and amount):
        raise ValueError("not a Shriram FD receipt (missing deposit no, dates or amount)")
    value = Decimal(amount[1].replace(",", ""))
    return Holding(as_of=_d(row[1]), source="shriram", account=no[1], isin=no[1],
                   name=f"Shriram FD {no[1]} @ {rate[1] if rate else '?'}%, {row[2]} at maturity",
                   units=Decimal(1), price=value, value=value, matures=_d(row[3]),
                   nominee="NA" if nominee.upper() in ("NA", "N.A.", "NIL", "-") else nominee)  # NA = receipt says none


def parse(path) -> list[Holding]:
    with pdfplumber.open(path) as pdf:
        return [holding_from_text("\n".join(p.extract_text() or "" for p in pdf.pages))]
