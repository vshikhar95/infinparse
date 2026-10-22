"""Amazon: the 'Request your data' export (Your Orders.zip), read in place. One purchase per order id (item rows
summed, cancelled items dropped) plus completed refunds. Address and gift columns are never read.
Digital Content Orders (Kindle, mostly free) are skipped."""
import csv
import io
import zipfile
from collections import Counter
from datetime import date
from decimal import Decimal

from purchase_history_parsers.models import Purchase

MAX_MEMBER_BYTES = 200 * 1024 * 1024  # a real export is a few MB; a zip bomb expands far past this
ORDERS = "Your Amazon Orders/Order History.csv"
REFUNDS = "Your Returns & Refunds/Refund Details.csv"


def _rows(z, name):
    if name not in z.namelist():
        return []
    if z.getinfo(name).file_size > MAX_MEMBER_BYTES:
        raise ValueError(f"{name.rsplit('/', 1)[-1]} in the zip is too large to be an Amazon export")
    return list(csv.DictReader(io.TextIOWrapper(z.open(name), "utf-8-sig")))


def _amt(s):
    return Decimal(s.replace(",", ""))


def parse(path):
    with zipfile.ZipFile(path) as z:
        orders, refunds = _rows(z, ORDERS), _rows(z, REFUNDS)
    out, by_id = [], {}
    for r in orders:
        if r["Order Status"] == "Cancelled":
            continue
        p = by_id.get(r["Order ID"])
        if p is None:
            pay = r["Payment Method Type"]
            p = by_id[r["Order ID"]] = Purchase(
                store="amazon", order_id=r["Order ID"], date=date.fromisoformat(r["Order Date"][:10]), items="",
                kind="purchase", amount=Decimal(0), currency=r["Currency"], payment=pay,
                charged=Decimal(0) if pay == "Gift Certificate/Card" else None, raw_type=r["Website"])
            out.append(p)
        p.items = " | ".join(filter(None, [p.items, r["Product Name"]]))
        p.amount += _amt(r["Total Amount"])
    seen = Counter()
    for r in refunds:
        if r["Disbursement Type"] != "Refund" or r["Reversal Status"] != "Completed" or not r["Refund Amount"][:1].isdigit():
            continue
        seen[r["Order ID"]] += 1
        out.append(Purchase(store="amazon", order_id=f"refund:{r['Order ID']}:{seen[r['Order ID']]}",
                            date=date.fromisoformat((r["Refund Date"] if r["Refund Date"][:1].isdigit() else r["Creation Date"])[:10]),
                            items=by_id[r["Order ID"]].items if r["Order ID"] in by_id else "",
                            kind="refund", amount=-_amt(r["Refund Amount"]), currency=r["Currency"], raw_type=r["Website"]))
    return out
