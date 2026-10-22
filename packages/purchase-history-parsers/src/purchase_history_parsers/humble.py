"""Humble Bundle: humble_orders.json exported from the logged-in /api/v1/order endpoints
(order metadata only; gamekeys hashed into `id`, no game keys). Old orders are USD, newer may be INR."""
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from purchase_history_parsers.models import Purchase


def parse(path):
    out = []
    for o in json.loads(Path(path).read_text()):
        amount = Decimal(str(o["amount_spent"] or 0))
        items = o["product"] + (": " + " | ".join(o["items"]) if o["items"] else "")
        out.append(Purchase(
            store="humble", order_id=o["id"], date=datetime.fromisoformat(o["created"]).date(), items=items,
            kind="purchase" if amount > 0 else "other", amount=amount, currency=o["currency"] or "",  # freebies: null
            raw_type="gift received" if o["is_giftee"] else o["category"] or "",
        ))
    return out
