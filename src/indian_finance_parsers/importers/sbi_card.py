"""SBI Card: 'Transaction_history.pdf' from the SBI Card site (covers up to 2 years back from download).
Columns sit at fixed x positions (Date | Description | Type | Amount). Wrapped descriptions spill above and below
their row, so words are assigned to the nearest dated row by position, not by text order."""
import re
from datetime import datetime
from decimal import Decimal

import pdfplumber

from indian_finance_parsers.models import Txn

DATE = re.compile(r"\d\d/\d\d/\d{4}$")
AMOUNT = re.compile(r"[\d,]+\.\d\d$")
DESC_X, TYPE_X, AMOUNT_X = 100, 365, 460  # column left edges (points)
MAX_GAP = 40  # a wrapped fragment further than this from any row is page furniture, not data


def parse(path):
    txns = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            txns += rows_from_words(page.extract_words())
    return sorted(txns, key=lambda t: t.date)  # history is newest-first


def rows_from_words(words):
    """Txns from one page's words ({"text","x0","top"}); nearest dated row owns each fragment."""
    txns = []
    header = next((w["top"] for w in words if w["text"] == "Description"), -1)
    anchors = [w for w in words if w["x0"] < DESC_X and DATE.match(w["text"]) and w["top"] > header]
    if not anchors:
        return txns
    rows = {id(a): {"date": a["text"], "desc": [], "type": [], "amt": []} for a in anchors}
    for w in words:
        if w["top"] <= header + 5 or w in anchors or w["x0"] < DESC_X:
            continue
        a = min(anchors, key=lambda a: abs(a["top"] - w["top"]))
        if abs(a["top"] - w["top"]) > MAX_GAP:
            continue
        col = "amt" if w["x0"] >= AMOUNT_X else "type" if w["x0"] >= TYPE_X else "desc"
        if col == "amt" and not AMOUNT.match(w["text"]):
            continue  # wrapped column header "Amount (Rs.)"
        rows[id(a)][col].append(w)
    for a in anchors:
        r = rows[id(a)]
        amount = Decimal("".join(w["text"] for w in r["amt"]).replace(",", "") or "0")
        kind = " ".join(w["text"] for w in r["type"])
        if amount == 0:
            continue  # memo rows (notes printed without an amount) carry no money
        if kind not in ("Debit", "Credit"):
            raise ValueError(f"unexpected type {kind!r} on {a['text']}")
        desc = " ".join(w["text"] for w in sorted(r["desc"], key=lambda w: (round(w["top"]), w["x0"])))
        txns.append(Txn(date=datetime.strptime(a["text"], "%d/%m/%Y").date(),
                        amount=-amount if kind == "Debit" else amount, description=desc))
    return txns


def meta(path):
    return {}
