"""Blinkit: blinkit-orders.PERSONAL.json from the exporter (order list + per-order bill; no address, phone or name).
`total` is the final bill; item `price` is a line total. Card digits are masked here too, for older exports."""
import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

from purchase_history_parsers.models import Purchase


def parse(path):
    out = []
    for o in json.loads(Path(path).read_text()):
        if not o["date"]:  # no date, no row (a Purchase needs one)
            continue
        total = Decimal(str(o["total"] or 0))
        items = " | ".join(i["name"] + (f" ×{i['qty']}" if i["qty"] > 1 else "") for i in o["items"])
        payment = re.sub(r"[\d*•]+|\bX{2,}\b", "", re.sub(r"\([^)]*\)", "", o["payment"] or ""), flags=re.IGNORECASE)
        out.append(Purchase(
            store="blinkit", order_id=o["id"], date=date.fromisoformat(o["date"]), items=items,
            kind="purchase" if o["status"] == "DELIVERED" and total > 0 else "other", amount=total,
            currency=o["currency"], payment=" ".join(payment.split()), raw_type=o["status"] or "",
        ))
    return out
