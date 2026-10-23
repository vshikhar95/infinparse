"""HDFC credit card statement PDF (the monthly emailed statement; password-protected).

Two layouts: 2024 ("dd/mm/yyyy hh:mm:ss  desc  [NeuCoins]  1,234.56[Cr]"; payments and refunds print no time:
"dd/mm/yyyy  desc  1,234.56Cr") and 2025+ ("dd/mm/yyyy| hh:mm  desc  [+] ₹ 1,234.56", '+' = credit). Rows are
rebuilt from word positions; the NeuCoins column is dropped by position. The rows must match the statement's summary
box (payments/credits and purchases/debits), so a dropped row rejects the file (see check_summary)."""
from pathlib import Path
import re
from datetime import datetime
from decimal import Decimal

import pdfplumber

from indian_finance_parsers.checks import check_totals
from indian_finance_parsers.models import Txn

DATE = re.compile(r"(\d\d/\d\d/\d{4})\|?$")
TIME = re.compile(r"\d\d:\d\d(:\d\d)?$")
AMOUNT = re.compile(r"[\d,]+\.\d\d(Cr)?$")
BOX_AMOUNT = re.compile(r"[C₹`]?([\d,]+\.\d\d)$")  # the 2025+ layout prints the ₹ sign as a "C" glyph


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
        summary = summary_from_words(pdf.pages[0].extract_words())
    name = Path(getattr(path, "name", path)).name
    if summary is None:
        raise ValueError(f"{name}: statement summary box not found, so the rows can't be checked")
    check_summary(summary, txns, name)
    return sorted(txns, key=lambda t: t.date)


def rows_from_words(rows, coins_x):
    """Txns from rows of {"text","x0"} words (left to right); coins_x = left edge of the NeuCoins column or None."""
    txns = []
    for n, r in enumerate(rows):
        m = DATE.match(r[0]["text"])
        timed = len(r) > 1 and bool(TIME.match(r[1]["text"]))  # payments in the 2024 layout print no time
        if not m or len(r) < (3 if timed else 2):
            continue
        amt_i = max((i for i, w in enumerate(r) if AMOUNT.match(w["text"])), default=None)
        if amt_i is None:
            continue
        raw = r[amt_i]["text"]
        if not timed and not raw.endswith("Cr"):
            continue  # untimed rows are payments/refunds; an untimed debit is the header's due-date line
        amount = Decimal(raw.removesuffix("Cr").replace(",", ""))
        body = r[2 if timed else 1:amt_i]
        # a credit's '+' sits right before the ₹ glyph; a '+' in the NeuCoins column is points earned
        credit = raw.endswith("Cr") or any(body[i]["text"] == "+" and body[i + 1]["text"] in ("C", "₹")
                                           for i in range(len(body) - 1))
        # drop the ₹ glyph, the '+' marker, and the NeuCoins column (by position) from the description
        body = [w for w in body if w["text"] not in ("+", "C", "₹", "`")
                and not (coins_x and w["x0"] >= coins_x - 8 and re.fullmatch(r"[+-]?\d+", w["text"]))]
        if not body:  # a long description is printed on the lines above and below the dated line instead
            body = [w for k in (n - 1, n + 1) if 0 <= k < len(rows) and not DATE.match(rows[k][0]["text"])
                    for w in rows[k]]
        # "EMI " before a merchant marks a charge as merely eligible for EMI conversion (statement legend); it is
        # still an ordinary charge, so the marker moves to notes. A lone "EMI" word is left alone.
        emi = len(body) > 1 and body[0]["text"] == "EMI"
        txns.append(Txn(date=datetime.strptime(m[1], "%d/%m/%Y").date(),
                        amount=amount if credit else -amount,
                        description=" ".join(w["text"] for w in body[emi:]), notes="EMI eligible" if emi else ""))
    return txns


def summary_from_words(words):
    """The summary box's five figures, left to right: opening (previous) balance, payments/credits,
    purchases/debits, finance charges, total due. Read by position below the box's first label in either layout;
    None unless the figures add up (opening - credits + debits + charges = total, within ₹1)."""
    anchor = next((w for w in words if w["text"] in ("Opening", "PREVIOUS")), None)
    if anchor is None:
        return None
    figures = sorted((w for w in words if anchor["top"] < w["top"] <= anchor["top"] + 35 and BOX_AMOUNT.match(w["text"])),
                     key=lambda w: w["x0"])
    if len(figures) != 5:
        return None
    opening, credits, debits, charges, total = (Decimal(BOX_AMOUNT.match(w["text"])[1].replace(",", "")) for w in figures)
    if abs(opening - credits + debits + charges - total) > 1:  # HDFC rounds the printed total (off by up to ₹1)
        return None
    return {"opening": opening, "credits": credits, "debits": debits, "charges": charges, "total": total}


def check_summary(summary, txns, name):
    """The rows against the box: credits = Payment/Credits; debits = Purchase/Debits, plus Finance Charges when those
    are printed as rows too."""
    check_totals(txns, name, credits=summary["credits"], debits=[summary["debits"], summary["debits"] + summary["charges"]])


def meta(path):
    """First 4 card digits from the statement filename ('NNNNXXXXXXXXXXNN_DD-MM-YYYY.PDF'): which card this is."""
    m = re.search(r"(\d{4})X+\d\d_\d\d-\d\d-\d{4}", str(getattr(path, "name", path)))  # a path or a decrypted file
    return {"bin4": m[1] if m else ""}
