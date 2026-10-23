"""ICICI credit cards: 'CreditCardStatement*.CSV' export. Two known variants share one header:
dd/mm/yyyy + 'CR' sign column, and dd-Mon-yy + signed amounts. Add-on cards appear as sections; one account."""
import csv
import re
from datetime import datetime
from decimal import Decimal

from indian_finance_parsers.models import Txn

DATE = re.compile(r"\d\d[/-](\d\d|[A-Za-z]{3})[/-]\d{2,4}$")
CARD = re.compile(r"\d{4}[\sX]+\d{3,4}$")  # section line, already masked by ICICI: "4111 XXXX XXXX 111"


def _date(s):
    for fmt in ("%d/%m/%Y", "%d-%b-%y", "%d-%b-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"unknown date format: {s!r}")


def parse(path):
    txns, card = [], ""
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        for row in csv.reader(f):
            if row and CARD.match(row[0].strip()):
                card = re.sub(r"\s+", " ", row[0].strip())
                continue
            if not row or not DATE.match(row[0].strip()):
                continue  # headers, card-number section lines, footers
            if len(row) != 7:
                raise ValueError(f"transaction line with {len(row)} fields, expected 7")
            amt = Decimal(row[5].replace(",", "").strip())  # + = charge, - = payment/refund
            if row[6].strip().upper() == "CR":
                amt = -abs(amt)
            txns.append(Txn(date=_date(row[0].strip()), amount=-amt, description=row[2].strip(),
                            notes=f"card {card}" if card else "",
                            ref=row[1].strip()))  # the SerNo column
    return sorted(txns, key=lambda t: t.date)  # stable: keeps same-day order


def meta(path):
    """Last 4 of the statement's 'Accountno:' (an account number ICICI prints for the card, not the card number)."""
    with open(path, encoding="utf-8", errors="replace") as f:
        first = next(csv.reader(f))
    digits = re.sub(r"\D", "", first[1] if len(first) > 1 else "")
    return {"acct4": digits[-4:]}
