"""Google Play: saved 'Order history – Google Play' page (play.google.com/store/account/orderhistory)."""
import hashlib
import re
from pathlib import Path
from collections import Counter
from datetime import datetime
from decimal import Decimal

from bs4 import BeautifulSoup

from purchase_history_parsers.models import Purchase

DATE = re.compile(r"^(\d{1,2}) (\w{3})\w* (\d{4})$")  # "1 Oct 2026", "19 Sept 2026"
STATUSES = {"Refunded", "Cancelled", "Canceled", "Pending", "Declined"}  # sit between title and date


def parse(path):
    soup = BeautifulSoup(Path(path).read_text(encoding="utf-8", errors="replace"), "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    lines = [line.strip() for line in (soup.body or soup).get_text("\n").splitlines() if line.strip()]
    lines = lines[lines.index("Order history"):]
    out, seen = [], Counter()
    for i in range(1, len(lines) - 1):
        m = DATE.match(lines[i])
        if not (m and lines[i + 1].startswith("₹")):
            continue
        j, status = i - 1, ""
        while lines[j] in STATUSES:
            status, j = lines[j], j - 1
        d = datetime.strptime(f"{m[1]} {m[2]} {m[3]}", "%d %b %Y").date()
        amount, title = Decimal(lines[i + 1][1:].replace(",", "")), lines[j]
        key = f"{d}|{title}|{amount}"  # page has no order ids; nth-occurrence keeps repeat renewals distinct
        seen[key] += 1
        out.append(Purchase(store="google_play", order_id=hashlib.sha1(f"{key}|{seen[key]}".encode()).hexdigest()[:16],
                            date=d, items=title, kind="purchase", amount=amount, currency="INR",
                            refunded=status == "Refunded", raw_type=status))
    return out
