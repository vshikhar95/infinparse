"""Sovereign Gold Bonds held in RBI/bank form (not demat): the RBI certificate PDF -> one Holding at cost
(units in grams × issue price), with its maturity date. Revaluing at today's gold rate is the caller's job."""
import re
from datetime import datetime
from decimal import Decimal

import pdfplumber

from indian_finance_parsers.models import Holding


def _d(s):
    return datetime.strptime(s.title(), "%d-%b-%Y").date()


def _nominees(text):
    """Names under "Nominee Details" (rows: serial, then the name), "; "-joined; "" if the section or its rows are absent.
    The column header (the line holding "Nominee Name") is skipped; words it lists after "Nominee Name" are further
    one-word columns (relationship, share), so as many trailing words are dropped from each row."""
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.strip() == "Nominee Details"), None)
    if start is None:
        return ""
    rest, extra = lines[start + 1:], 0
    if rest and "Nominee Name" in rest[0]:
        extra = len(rest[0].split("Nominee Name", 1)[1].split())
        rest = rest[1:]
    names = []
    for ln in rest:
        m = re.fullmatch(r"\s*\d{1,2} (\S.*?)\s*", ln)
        if not m:
            break
        words = m[1].split()
        names.append(" ".join(words[:-extra] if extra and len(words) > extra else words))
    return "; ".join(names)


def holding_from_text(text) -> Holding:
    isin = re.search(r"Security Code (IN\w{10})(?: \d+)? - (SGB [\w-]+ SERIES \w+)", text)
    settled = re.search(r"Settlement Date (\d\d-[A-Z]{3}-\d{4})", text)
    units = re.search(r"Number of Units (\d+) Issue Price ([\d.]+)", text)
    matures = re.search(r"Maturity Date (\d\d-[A-Z]{3}-\d{4})", text)
    if not (isin and settled and units and matures):
        raise ValueError("not an RBI SGB certificate (missing security code, dates or units)")
    grams, price = Decimal(units[1]), Decimal(units[2])
    paid = re.search(r"Consideration Amount\s*[`₹]?\s*([\d,]+\.\d\d)", text)  # what was paid, as the certificate states it
    return Holding(as_of=_d(settled[1]), source="sgb", account=isin[1], name=isin[2], isin=isin[1],
                   units=grams, price=price, value=grams * price, matures=_d(matures[1]),
                   nominee=_nominees(text), cost=Decimal(paid[1].replace(",", "")) if paid else None)


def parse(path) -> list[Holding]:
    with pdfplumber.open(path) as pdf:
        return [holding_from_text("\n".join(p.extract_text() or "" for p in pdf.pages))]
