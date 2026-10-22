"""ICICI credit card statement PDF (the monthly emailed statement; password-protected).
Filenames name the card product: '<card>_<n>_Retail_<Product>_NORM.pdf'; meta() returns it as `product`.
Rows: 'dd/mm/yyyy <ref> <description> <reward points> <amount>[ CR]'; add-on cards appear as section lines.
The CSV export (icici_card.py) covers the same rows; a caller loading both should dedupe on date + amount."""
import re
from datetime import datetime
from decimal import Decimal

import pdfplumber

from indian_finance_parsers.models import Txn

# date, ref, description, [reward points], [foreign amount [currency]], INR amount, [CR]
ROW = re.compile(r"^(\d\d/\d\d/\d{4}) (\d{8,}) (.*?)(?: -?\d+)?(?: [\d,]*\.\d+(?: [A-Z]{3})?)? ([\d,]+\.\d\d)( CR)?$")
CARD = re.compile(r"^\d{4}X{6,}\d{4}$")  # add-on card section line, masked by ICICI


def parse(path):
    with pdfplumber.open(path) as pdf:
        lines = [ln for page in pdf.pages for ln in _table_text(page).splitlines()]
        summary = _summary(pdf.pages[0])
    txns = rows_from_lines(lines)
    if summary and txns:
        check_totals(summary, txns)
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
    """STATEMENT SUMMARY row: Previous Balance, Purchases/Charges, Cash Advances, Payments/Credits ('`1,234.56'),
    read left to right under the 'Previous' label. None if the layout isn't there."""
    words = page.extract_words()
    label = next((w for w in words if w["text"] == "Previous"), None)
    if label is None:
        return None
    vals = sorted((w for w in words if w["text"].startswith("`") and 0 < w["top"] - label["top"] < 30
                   and w["x0"] > label["x0"] - 30), key=lambda w: w["x0"])
    if len(vals) != 4:
        return None
    return [Decimal(w["text"].lstrip("`").replace(",", "")) for w in vals]


def check_totals(summary, txns):
    """Rows must add up to the statement's own Purchases+Cash and Payments/Credits totals."""
    _prev, purchases, cash, credits = summary
    debit = -sum(t.amount for t in txns if t.amount < 0)
    credit = sum(t.amount for t in txns if t.amount > 0)
    if debit != purchases + cash or credit != credits:
        raise ValueError(f"rows don't match statement totals (debits {'ok' if debit == purchases + cash else 'off'}, "
                         f"credits {'ok' if credit == credits else 'off'})")


def meta(path):
    m = re.search(r"_Retail_(\w+?)_", str(path))
    return {"product": m[1] if m else "Unknown"}
