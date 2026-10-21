"""PlayStation Store receipt email saved as HTML ("Thank You For Your Purchase", pre-order confirmations).
One order per file. ₹0 orders (PS Plus claims) are kept but flagged, not counted as purchases."""
import html
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from indian_finance_parsers.models import Purchase

RS = r"Rs ([\d,]+(?:\.\d\d)?)"
CARD = re.compile(r"(VISA|MasterCard|MC|AMEX|American Express|RuPay)\s*(\d{4})\*+(\d{4})\s*:\s*" + RS)


def _money(s):
    return Decimal(s.replace(",", ""))


def _text(raw):
    t = re.sub(r"<style.*?</style>|<[^>]+>", " ", raw, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def parse(path):
    t = _text(Path(path).read_text(encoding="utf-8", errors="replace"))
    order = re.search(r"Order Number: (\d+)", t)
    when = re.search(r"(?:Date Purchased|Date and time of purchase): (\d\d/\d\d/\d{4})", t)  # new | old layout
    total = re.search(r"Total: " + RS, t)
    if not (order and when and total):
        raise ValueError("not a PlayStation purchase receipt (missing order number, date or total)")
    start = re.search(r"Details (?:Unit of )?Price", t) or re.search(r"$", t)  # no Details heading: no items
    end = min((i for i in (t.find("Subtotal:"), t.find("Current Wallet Amount"), t.find("Total:")) if i > start.end()),
              default=len(t))
    details = t[start.end():end]
    details = re.sub(r"Recurring Subscription Fee: " + RS + r" will be charged on \S+", "", details)
    items = [i.strip() for i in re.split(RS, details)[::2] if i.strip()]
    cards = CARD.findall(t[total.end():])
    amount = _money(total[1])
    return [Purchase(
        store="playstation", order_id=order[1], date=datetime.strptime(when[1], "%d/%m/%Y").date(),
        items=" | ".join(items), kind="purchase" if amount > 0 else "other", amount=amount, currency="INR",
        payment=", ".join(f"{n} {a}…{b}" for n, a, b, _ in cards),
        charged=sum((_money(c[3]) for c in cards), Decimal(0)) if cards else None,
        raw_type="purchase" if amount > 0 else "free (likely PS Plus)",
    )]
