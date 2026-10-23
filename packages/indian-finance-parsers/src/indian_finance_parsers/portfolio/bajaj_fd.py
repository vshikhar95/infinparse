"""Bajaj Finance FD receipts (deposit detail PDFs; some password-protected) -> one Holding per deposit, as the receipt
states it: dated at the deposit date, valued at the deposit amount, with its maturity date. Whether it has matured,
and what it is worth today, is the caller's judgement. `deposits(path)` returns the receipt's terms (rate, tenure,
scheme, payout) as a Deposit."""
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pdfplumber

from indian_finance_parsers.checks import check_deposit
from indian_finance_parsers.models import Deposit, Holding

D8 = r"(\d\d-\d\d-\d{4})"
AMT = r"([\d,]+\.\d\d)"
# deposit date, scheme, "<months>M <days>D", maturity date, rate, deposit amount, interest amount, maturity amount
ROW = re.compile(rf"{D8} ([A-Za-z][\w -]*?) (\d+)M (\d+)D {D8} (\d+(?:\.\d+)?)% {AMT} {AMT} {AMT}")


def _d(s):
    return datetime.strptime(s, "%d-%m-%Y").date()


def _money(s):
    return Decimal(s.replace(",", ""))


def deposit_from_text(text, name="receipt") -> Deposit:
    """The receipt's terms as printed. Raises ValueError (naming `name` and the field) if they contradict each other:
    deposit amount + interest amount must equal the maturity amount (within ₹1), plus the checks.check_deposit ones."""
    no = re.search(r"DEPOSIT NUMBER: (\d+)", text)
    row = ROW.search(text)
    if "Bajaj Finance" not in text or not (no and row):
        raise ValueError("not a Bajaj Finance FD receipt (missing deposit number or the deposit row)")
    payout = re.search(r"Interest Payment \w+ ?: (.+)$", text, re.M)
    nominees = "; ".join(n for n in (m.strip() for m in re.findall(r"Nominee \d+ ?:[ \t]*(.*)$", text, re.M)) if n)
    amount, interest, maturity = _money(row[7]), _money(row[8]), _money(row[9])
    if abs(amount + interest - maturity) > 1:
        raise ValueError(f"{name}: maturity_amount doesn't equal the deposit amount plus the interest amount")
    d = Deposit(deposit_no=no[1], deposited=_d(row[1]), amount=amount, rate=Decimal(row[6]),
                tenure_months=int(row[3]), matures=_d(row[5]), maturity_amount=maturity, scheme=row[2],
                interest_payout=payout[1].strip() if payout else "",
                nominee="NA" if nominees.upper() in ("NA", "N.A.", "NIL", "-") else nominees)  # NA = receipt says none
    check_deposit(d, name)
    return d


def holding_from_text(text, name="receipt") -> Holding:
    d = deposit_from_text(text, name)
    return Holding(as_of=d.deposited, source="bajaj", account=d.deposit_no, isin=d.deposit_no,
                   name=f"Bajaj Finance FD {d.deposit_no} @ {d.rate}%, {d.maturity_amount} at maturity",
                   units=Decimal(1), price=d.amount, value=d.amount, matures=d.matures, nominee=d.nominee)


def _read(path, fn):
    name = Path(getattr(path, "name", path)).name
    with pdfplumber.open(path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    try:
        return fn(text, name)
    except ValueError as e:
        raise ValueError(e if str(e).startswith(name) else f"{name}: {e}") from None


def parse(path) -> list[Holding]:
    return [_read(path, holding_from_text)]


def deposits(path) -> list[Deposit]:
    return [_read(path, deposit_from_text)]
