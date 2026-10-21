"""HDFC credit card statement PDF (the monthly emailed statement; password-protected).

Two layouts: 2024 ("dd/mm/yyyy hh:mm:ss  desc  [NeuCoins]  1,234.56[Cr]") and 2025+ ("dd/mm/yyyy| hh:mm  desc
[+] ₹ 1,234.56", '+' = credit). Rows are rebuilt from word positions; the NeuCoins column is dropped by position.
Statement totals are checked against the rows (see check_totals)."""
import re
from datetime import datetime
from decimal import Decimal

import pdfplumber

from indian_finance_parsers.models import Txn

DATE = re.compile(r"(\d\d/\d\d/\d{4})\|?$")
TIME = re.compile(r"\d\d:\d\d(:\d\d)?$")
AMOUNT = re.compile(r"[\d,]+\.\d\d(Cr)?$")


def _rows(page):
    lines = {}
    for w in page.extract_words():
        lines.setdefault(round(w["top"]), []).append(w)
    return [sorted(ws, key=lambda w: w["x0"]) for _, ws in sorted(lines.items())]


def parse(path):
    txns = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            coins_x = next((w["x0"] for w in page.extract_words() if w["text"].startswith("NeuCoins*")), None)
            txns += rows_from_words(_rows(page), coins_x)
        check_totals("\n".join(p.extract_text() or "" for p in pdf.pages), txns)
    return sorted(txns, key=lambda t: t.date)


def rows_from_words(rows, coins_x):
    """Txns from rows of {"text","x0"} words (left to right); coins_x = left edge of the NeuCoins column or None."""
    txns = []
    for n, r in enumerate(rows):
        m = DATE.match(r[0]["text"])
        if not m or len(r) < 3 or not TIME.match(r[1]["text"]):
            continue
        amt_i = max((i for i, w in enumerate(r) if AMOUNT.match(w["text"])), default=None)
        if amt_i is None:
            continue
        raw = r[amt_i]["text"]
        amount = Decimal(raw.removesuffix("Cr").replace(",", ""))
        body = r[2:amt_i]
        # a credit's '+' sits right before the ₹ glyph; a '+' in the NeuCoins column is points earned
        credit = raw.endswith("Cr") or any(body[i]["text"] == "+" and body[i + 1]["text"] in ("C", "₹")
                                           for i in range(len(body) - 1))
        # drop the ₹ glyph, the '+' marker, and the NeuCoins column (by position) from the description
        body = [w for w in body if w["text"] not in ("+", "C", "₹", "`")
                and not (coins_x and w["x0"] >= coins_x - 8 and re.fullmatch(r"[+-]?\d+", w["text"]))]
        if not body:  # a long description is printed on the lines above and below the dated line instead
            body = [w for k in (n - 1, n + 1) if 0 <= k < len(rows) and not DATE.match(rows[k][0]["text"])
                    for w in rows[k]]
        txns.append(Txn(date=datetime.strptime(m[1], "%d/%m/%Y").date(),
                        amount=amount if credit else -amount,
                        description=" ".join(w["text"] for w in body)))
    return txns


def check_totals(text, txns):
    """Previous dues + rows = total due: some pair of amounts printed in the statement must differ by exactly the
    net of the parsed rows. Catches dropped rows and flipped signs (e.g. a NeuCoins '+' read as a credit).
    ponytail: matches against any printed pair rather than locating the labelled boxes, which move between layouts."""
    printed = {Decimal(x.replace(",", "")) for x in re.findall(r"[\d,]+\.\d\d", text)}
    diffs = {b - a for a in printed for b in printed} | printed
    net = -sum(t.amount for t in txns)
    finance = -sum(t.amount for t in txns if t.description.startswith("FINANCE CHARGES"))  # summed outside the totals
    if net not in diffs and net - finance not in diffs:
        raise ValueError("rows don't reconcile with the statement totals (missing row or wrong sign?)")


def meta(path):
    """First 4 card digits from the statement filename ('NNNNXXXXXXXXXXNN_DD-MM-YYYY.PDF'): which card this is."""
    m = re.search(r"(\d{4})X+\d\d_\d\d-\d\d-\d{4}", str(path))
    return {"bin4": m[1] if m else ""}
