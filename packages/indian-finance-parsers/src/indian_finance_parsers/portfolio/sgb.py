"""Sovereign Gold Bonds held in RBI/bank form (not demat): the RBI certificate PDF -> one Holding at cost
(units in grams × issue price), with its maturity date. Revaluing at today's gold rate is the caller's job."""
import re
from datetime import datetime
from decimal import Decimal

import pdfplumber

from indian_finance_parsers.models import Holding


def holding_from_text(text) -> Holding:
    isin = re.search(r"Security Code (IN\w{10})(?: \d+)? - (SGB [\w-]+ SERIES \w+)", text)
    settled = re.search(r"Settlement Date (\d\d-[A-Z]{3}-\d{4})", text)
    units = re.search(r"Number of Units (\d+) Issue Price ([\d.]+)", text)
    matures = re.search(r"Maturity Date (\d\d-[A-Z]{3}-\d{4})", text)
    if not (isin and settled and units and matures):
        raise ValueError("not an RBI SGB certificate (missing security code, dates or units)")
    d = lambda s: datetime.strptime(s.title(), "%d-%b-%Y").date()
    grams, price = Decimal(units[1]), Decimal(units[2])
    return Holding(as_of=d(settled[1]), source="sgb", account=isin[1], name=isin[2], isin=isin[1],
                   units=grams, price=price, value=grams * price, matures=d(matures[1]))


def parse(path) -> list[Holding]:
    with pdfplumber.open(path) as pdf:
        return [holding_from_text("\n".join(p.extract_text() or "" for p in pdf.pages))]
