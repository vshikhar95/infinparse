"""Sovereign Gold Bonds held in RBI/bank form (not demat): the RBI certificate PDF -> one Holding at cost.
fetch_rate() + revalue() value them at the IBJA 999 gold rate, which is what RBI redeems at. fetch_rate() is the
only network call in this package; parse() never makes it."""
import re
import urllib.request
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

import pdfplumber

from indian_finance_parsers.models import Holding

IBJA = "https://ibjarates.com/"


def holding_from_text(text, owner):
    isin = re.search(r"Security Code (IN\w{10})(?: \d+)? - (SGB [\w-]+ SERIES \w+)", text)
    settled = re.search(r"Settlement Date (\d\d-[A-Z]{3}-\d{4})", text)
    units = re.search(r"Number of Units (\d+) Issue Price ([\d.]+)", text)
    matures = re.search(r"Maturity Date (\d\d-[A-Z]{3}-\d{4})", text)
    if not (isin and settled and units and matures):
        raise ValueError("not an RBI SGB certificate (missing security code, dates or units)")
    d = lambda s: datetime.strptime(s.title(), "%d-%b-%Y").date()
    grams, price = Decimal(units[1]), Decimal(units[2])
    return Holding(as_of=d(settled[1]), source="sgb", account=isin[1], name=f"{isin[2]} (matures {d(matures[1])})",
                   isin=isin[1], units=grams, price=price, value=grams * price, owner=owner)


def ibja_999(html) -> Decimal:
    """Per-gram 999 gold rate; IBJA publishes per 10g, AM then PM (PM preferred once out)."""
    rates = dict(re.findall(r'lblGold999_(AM|PM)">\s*([\d.]+)', html))
    if not rates:
        raise ValueError("IBJA page has no 999 gold rate")
    return Decimal(rates.get("PM") or rates["AM"]) / 10


def fetch_rate() -> Decimal:
    req = urllib.request.Request(IBJA, headers={"User-Agent": "indian-finance-parsers (+https://github.com/vshikhar95/indian-finance-parsers)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return ibja_999(r.read().decode("utf-8", "replace"))


def revalue(h, rate, today):
    units = Decimal(str(h.units))  # tolerate text, e.g. when read back from sqlite
    return replace(h, as_of=today, units=units, price=rate, value=units * rate)


def parse(path, owner="unconfirmed"):
    with pdfplumber.open(path) as pdf:
        return [holding_from_text("\n".join(p.extract_text() or "" for p in pdf.pages), owner)]
