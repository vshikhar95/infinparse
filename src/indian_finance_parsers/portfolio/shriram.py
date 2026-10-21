"""Shriram Finance FD receipts (deposit advice PDFs; some password-protected) -> one Holding per deposit.
An open FD counts at its deposit amount (accrued interest ignored); one past its maturity date counts 0."""
import re
from datetime import date, datetime
from decimal import Decimal

import pdfplumber

from indian_finance_parsers.models import Holding

D8 = r"(\d\d-\d\d-\d{4})"


def _d(s):
    return datetime.strptime(s, "%d-%m-%Y").date()


def fd_from_text(text):
    no = re.search(r"Deposit No\. ([A-Z]+-\d+)", text)
    row = re.search(D8 + r" \d+ \*?([\d,]+\.\d\d) " + D8, text)  # deposit date, months, maturity amount, maturity date
    amount = re.search(r"Deposit Amount : ₹?([\d,]+\.\d\d)", text)
    rate = re.search(r"([\d.]+) % p\.a\.", text)
    if not (no and row and amount):
        raise ValueError("not a Shriram FD receipt (missing deposit no, dates or amount)")
    return {"deposit_no": no[1], "deposited": _d(row[1]), "amount": Decimal(amount[1].replace(",", "")),
            "rate": Decimal(rate[1]) if rate else None, "matures": _d(row[3]),
            "maturity_amount": Decimal(row[2].replace(",", ""))}


def holdings_from_text(text, today, owner):
    fd = fd_from_text(text)
    matured = fd["matures"] <= today
    # ponytail: maturity is judged when the receipt is parsed; re-parse the receipt to refresh it
    return [Holding(as_of=fd["matures"] if matured else fd["deposited"], source="shriram", account=fd["deposit_no"],
                    name=f"Shriram FD {fd['deposit_no']} @ {fd['rate']}% to {fd['matures']}, {fd['maturity_amount']} at maturity", isin=fd["deposit_no"],
                    units=Decimal(1), price=Decimal(0) if matured else fd["amount"],
                    value=Decimal(0) if matured else fd["amount"], owner=owner)]


def parse(path, owner="unconfirmed"):
    with pdfplumber.open(path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    return holdings_from_text(text, date.today(), owner)
