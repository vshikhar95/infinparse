"""Shriram Finance FD receipts (deposit advice PDFs; some password-protected) -> one Holding per deposit, as the
receipt states it: dated at the deposit date, valued at the deposit amount, with its maturity date. Whether it has
matured, and what it is worth today, is the caller's judgement."""
import re
from datetime import datetime
from decimal import Decimal

import pdfplumber

from pathlib import Path

from indian_finance_parsers.checks import check_deposit
from indian_finance_parsers.models import Deposit, Holding

D8 = r"(\d\d-\d\d-\d{4})"


def _d(s):
    return datetime.strptime(s, "%d-%m-%Y").date()


def _fields(text):
    no = re.search(r"Deposit No\. ([A-Z]+-\d+)", text)
    row = re.search(D8 + r" (\d+) \*?([\d,]+\.\d\d) " + D8, text)  # deposit date, months, maturity amount, maturity date
    amount = re.search(r"Deposit Amount : ₹?([\d,]+\.\d\d)", text)
    rate = re.search(r"(?<![\d.])([\d.]{1,8}) % p\.a\.", text)
    nominee = (re.search(r"Nominee : (.+)", text) or [None, ""])[1].strip()
    if not (no and row and amount):
        raise ValueError("not a Shriram FD receipt (missing deposit no, dates or amount)")
    return no, row, amount, rate, "NA" if nominee.upper() in ("NA", "N.A.", "NIL", "-") else nominee  # NA = receipt says none


def holding_from_text(text) -> Holding:
    no, row, amount, rate, nominee = _fields(text)
    value = Decimal(amount[1].replace(",", ""))
    return Holding(as_of=_d(row[1]), source="shriram", account=no[1], isin=no[1],
                   name=f"Shriram FD {no[1]} @ {rate[1] if rate else '?'}%, {row[3]} at maturity",
                   units=Decimal(1), price=value, value=value, matures=_d(row[4]), nominee=nominee)


def deposit_from_text(text, name="receipt") -> Deposit:
    """The receipt's terms as printed. Raises ValueError (naming `name` and the field) if they contradict each other."""
    no, row, amount, rate, nominee = _fields(text)
    scheme = re.search(r"Deposit No\. \S+ Scheme (.+)", text)
    payout = re.search(r"Interest \w+ ?: (.+)$", text, re.M)
    try:
        pct = Decimal(rate[1]) if rate else None
    except ArithmeticError:
        raise ValueError(f"{name}: rate is unreadable") from None
    d = Deposit(deposit_no=no[1], deposited=_d(row[1]), amount=Decimal(amount[1].replace(",", "")), rate=pct,
                tenure_months=int(row[2]), matures=_d(row[4]), maturity_amount=Decimal(row[3].replace(",", "")),
                scheme=scheme[1].strip() if scheme else "", interest_payout=payout[1].strip() if payout else "",
                nominee=nominee)
    check_deposit(d, name)
    return d


def parse(path) -> list[Holding]:
    with pdfplumber.open(path) as pdf:
        return [holding_from_text("\n".join(p.extract_text() or "" for p in pdf.pages))]


def deposits(path) -> list[Deposit]:
    """Optional extra next to parse(): the receipt's terms (rate, tenure, scheme, payout) as a Deposit."""
    name = Path(getattr(path, "name", path)).name
    with pdfplumber.open(path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    try:
        return [deposit_from_text(text, name)]
    except ValueError as e:
        raise ValueError(e if str(e).startswith(name) else f"{name}: {e}") from None
