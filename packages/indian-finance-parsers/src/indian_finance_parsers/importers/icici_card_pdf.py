"""ICICI credit card statement PDF (the monthly emailed statement; password-protected).
Filenames name the card product: '<card>_<n>_Retail_<Product>_NORM.pdf'; meta() returns it as `product`.
Rows: 'dd/mm/yyyy <ref> <description> <reward points> <amount>[ CR]'; add-on cards appear as section lines.
The CSV export (icici_card.py) covers the same rows; a caller loading both should dedupe on date + amount."""
import re
from pathlib import Path
from datetime import datetime
from decimal import Decimal

import pdfplumber

from indian_finance_parsers._words import below, label, norm, read
from indian_finance_parsers.checks import check_card_summary, check_totals
from indian_finance_parsers.models import CardSummary, Txn

# date, ref, description, [reward points], [foreign amount [currency]], INR amount, [CR]
ROW = re.compile(r"^(\d\d/\d\d/\d{4}) (\d{8,}) (.*?)(?: -?\d+)?(?: [\d,]*\.\d+(?: [A-Z]{3})?)? ([\d,]+\.\d\d)( CR)?$")
CARD = re.compile(r"^\d{4}X{6,}\d{4}$")  # add-on card section line, masked by ICICI


def parse(path):
    with pdfplumber.open(path) as pdf:
        lines = [ln for page in pdf.pages for ln in _table_text(page).splitlines()]
        summary = _summary(pdf.pages[0])
    txns = rows_from_lines(lines)
    if summary and txns:
        check_summary(summary, txns, Path(getattr(path, "name", path)).name)
    return sorted(txns, key=lambda t: t.date)


def rows_from_lines(lines):
    """Txns from table text lines; a card section line sets the notes of the rows after it."""
    txns, card = [], ""
    for line in lines:
        line = line.strip()
        if CARD.match(line):
            card = f"card {line[:4]} XXXX XXXX {line[-4:]}"
            continue
        m = ROW.match(line)
        if not m:
            continue
        amount = Decimal(m[4].replace(",", ""))
        txns.append(Txn(date=datetime.strptime(m[1], "%d/%m/%Y").date(),
                        amount=amount if m[5] else -amount, description=m[3].strip(), notes=card))
    return txns


def _table_text(page):
    """Text of the transaction table only. Newer statements put a side panel (offers, EMI notes) next to the
    table, and plain extract_text() merges panel lines into rows at the same height; cropping to the area
    right of / below the 'Date SerNo.' header keeps rows intact. Pages without the header are read whole."""
    words = page.extract_words()
    hdr = next((w for i, w in enumerate(words[:-1]) if w["text"] == "Date" and words[i + 1]["text"].startswith("SerNo")),
               None)
    if hdr is None:
        return page.extract_text() or ""
    return page.crop((max(hdr["x0"] - 3, 0), hdr["top"], page.width, page.height)).extract_text() or ""


def _summary(page):
    """The four STATEMENT SUMMARY figures as positive numbers (what the rows are checked against), or None."""
    vals = _figures(page.extract_words())
    return vals and [abs(v) for v in vals]


def _figures(words):
    """STATEMENT SUMMARY row: Previous Balance, Purchases/Charges, Cash Advances, Payments/Credits ('`1,234.56'),
    read left to right under the 'Previous' label. A figure followed by a separate 'CR' word is a credit balance
    and comes back negative. None if the layout isn't there."""
    lab = next((w for w in words if norm(w["text"]) == "Previous"), None)
    if lab is None:
        return None
    vals = sorted((w for w in words if re.fullmatch(FIG, w["text"]) and 0 < w["top"] - lab["top"] < 30
                   and w["x0"] > lab["x0"] - 30), key=lambda w: w["x0"])
    if len(vals) != 4:
        return None
    return [(-1 if any(c["text"] == "CR" and abs(c["top"] - w["top"]) < 3 and 0 <= c["x0"] - w["x1"] < 12
                       for c in words) else 1) * Decimal(w["text"].lstrip("`").replace(",", "")) for w in vals]


def summary(path) -> CardSummary:
    """The statement's header figures: dates, total and minimum due, the summary row, and the limits. Optional extra
    next to parse(); raises ValueError (file + field) if a figure is missing, the summary row doesn't add up to the
    total due, or the figures are inconsistent."""
    with pdfplumber.open(path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
        return card_summary(pdf.pages[0].extract_words(), Path(getattr(path, "name", path)).name, text)


MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
DAY = rf"{MONTH} \d\d?, \d{{4}}"
PERIOD = re.compile(rf"Statement period\s*:\s*({DAY}) to ({DAY})")
FIG = r"`\d[\d,]*(?:\.\d\d)?"
MONEY = r"`\d[\d,]*\.\d\d(?: CR)?"


def _day(t):
    for f in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(t, f).date()
        except ValueError:
            pass
    raise ValueError


def card_summary(words, name, text="") -> CardSummary:
    """CardSummary from page-0 words ({"text","x0","x1","top"}) and the whole statement's text (for the period, which
    is optional). Cash advances go in `cash_advances`: ICICI prints no finance-charges figure. Previous balance and
    total due may be credit balances ('CR'), which come back negative; the summary row must give the total due:
    previous + purchases + cash advances - payments (within ₹1)."""
    row = _figures(words)
    if row is None:
        raise ValueError(f"{name}: statement summary row not found")

    def need(field, v):
        if v is None:
            raise ValueError(f"{name}: {field} not found")
        return v

    def money(field, *words_, pad=10):
        t = need(field, below(words, label(words, *words_), MONEY, pad=pad))
        return (-1 if t.endswith(" CR") else 1) * read(name, field, Decimal, re.sub(r"[^\d.]", "", t))

    total = money("total_due", "Total", "Amount", "due", pad=30)  # a trailing CR sits just past the label's width
    lab = label(words, "Credit", "Limit")
    limits = sorted((w for w in words if lab and re.fullmatch(FIG, w["text"])
                     and 0 < w["top"] - lab["top"] <= 30 and w["x0"] > lab["x0"] - 30), key=lambda w: w["x0"])
    if len(limits) != 4:
        raise ValueError(f"{name}: credit limits not found")
    limit, avail, cash_limit, avail_cash = (read(name, "credit limits", Decimal, w["text"][1:].replace(",", "")) for w in limits)
    prev, purchases, cash_adv, payments = row
    if abs(prev + purchases + cash_adv - payments - total) > 1:
        raise ValueError(f"{name}: total_due doesn't follow from the summary row (previous + purchases + cash "
                         "advances - payments)")
    period = PERIOD.search(text)
    def day(field, t):
        return read(name, field, _day, need(field, t))

    s = CardSummary(statement_date=day("statement_date", below(words, label(words, "STATEMENT", "DATE"), DAY)),
                    due_date=day("due_date", below(words, label(words, "PAYMENT", "DUE", "DATE"), DAY)),
                    total_due=total, minimum_due=money("minimum_due", "Minimum", "Amount", "due", pad=30),
                    previous_balance=prev, payments=payments, purchases=purchases, cash_advances=cash_adv,
                    credit_limit=limit, available_credit=avail, cash_limit=cash_limit, available_cash=avail_cash,
                    period_start=day("period", period[1]) if period else None,
                    period_end=day("period", period[2]) if period else None)
    check_card_summary(s, name)
    return s


def check_summary(summary, txns, name="statement"):
    """Rows must add up to the statement's own Purchases+Cash and Payments/Credits totals."""
    _prev, purchases, cash, credits = summary
    check_totals(txns, name, credits=credits, debits=purchases + cash)


def meta(path):
    m = re.search(r"_Retail_(\w+?)_", str(getattr(path, "name", path)))  # a path or a decrypted file
    return {"product": m[1] if m else "Unknown"}
