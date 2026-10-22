"""Amazon 'Request your data' export (Your Orders.zip): orders grouped per order id, cancellations dropped, refunds."""
import csv
import io
import zipfile
from datetime import date
from decimal import Decimal as D

from purchase_history_parsers import amazon

ORDER_COLS = ["Order ID", "Order Date", "Website", "Currency", "Product Name", "Total Amount", "Order Status",
              "Payment Method Type", "Shipping Address"]
REFUND_COLS = ["Order ID", "Refund Date", "Creation Date", "Currency", "Refund Amount", "Disbursement Type", "Reversal Status", "Website"]


def _csv(cols, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, cols)
    w.writeheader()
    w.writerows(rows)
    return "﻿" + buf.getvalue()  # Amazon writes a BOM


def _zip(tmp_path, orders, refunds):
    p = tmp_path / "Your Orders.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("Your Amazon Orders/Order History.csv", _csv(ORDER_COLS, orders))
        z.writestr("Your Returns & Refunds/Refund Details.csv", _csv(REFUND_COLS, refunds))
    return p


def o(oid, day, name, total, status="Closed", pay="Visa - 1111", site="Amazon.in", cur="INR"):
    return {"Order ID": oid, "Order Date": f"2026-01-{day:02d}T10:00:00Z", "Website": site, "Currency": cur,
            "Product Name": name, "Total Amount": total, "Order Status": status, "Payment Method Type": pay,
            "Shipping Address": "SECRET ADDRESS"}


def test_items_of_one_order_become_one_purchase(tmp_path):
    p = _zip(tmp_path, [o("A1", 5, "Kettle", "1,299"), o("A1", 5, "Mug", "200")], [])
    [x] = amazon.parse(p)
    assert (x.store, x.order_id, x.date, x.items, x.kind, x.amount, x.currency, x.payment) == (
        "amazon", "A1", date(2026, 1, 5), "Kettle | Mug", "purchase", D("1499"), "INR", "Visa - 1111")
    assert "SECRET" not in repr(x)


def test_cancelled_items_are_dropped_and_fully_cancelled_orders_vanish(tmp_path):
    p = _zip(tmp_path, [o("A1", 5, "Kettle", "1299"), o("A1", 5, "Mug", "200", status="Cancelled"),
                        o("A2", 6, "Lamp", "999", status="Cancelled")], [])
    assert [(x.order_id, x.items, x.amount) for x in amazon.parse(p)] == [("A1", "Kettle", D("1299"))]


def test_gift_card_orders_charge_no_real_account(tmp_path):
    p = _zip(tmp_path, [o("A1", 5, "Book", "349", pay="Gift Certificate/Card"),
                        o("A2", 6, "Pen", "50", pay="Gift Certificate/Card and Visa - 1111")], [])
    assert [(x.order_id, x.charged) for x in amazon.parse(p)] == [("A1", D(0)), ("A2", None)]


def test_completed_refunds_are_negative_rows_keyed_per_order(tmp_path):
    refund = {"Order ID": "A1", "Refund Date": "2026-01-20T10:00:00Z", "Currency": "INR", "Refund Amount": "2,399",
              "Disbursement Type": "Refund", "Reversal Status": "Completed", "Website": "Amazon.in"}
    other = dict(refund, **{"Disbursement Type": "FATEReport"})
    rows = amazon.parse(_zip(tmp_path, [o("A1", 5, "Shoes", "2399")], [refund, refund, other]))
    refunds = [(x.order_id, x.kind, x.date, x.amount) for x in rows if x.kind == "refund"]
    assert refunds == [("refund:A1:1", "refund", date(2026, 1, 20), D("-2399")),
                       ("refund:A1:2", "refund", date(2026, 1, 20), D("-2399"))]


def test_refund_without_a_refund_date_uses_its_creation_date(tmp_path):
    refund = {"Order ID": "A1", "Refund Date": "Not Applicable", "Creation Date": "2026-01-18T10:00:00Z", "Currency": "INR",
              "Refund Amount": "10", "Disbursement Type": "Refund", "Reversal Status": "Completed", "Website": "Amazon.in"}
    rows = amazon.parse(_zip(tmp_path, [], [refund]))
    assert [(x.date, x.amount) for x in rows] == [(date(2026, 1, 18), D("-10"))]


def test_refund_without_an_amount_is_skipped(tmp_path):
    refund = {"Order ID": "A1", "Refund Date": "2026-01-20T10:00:00Z", "Creation Date": "", "Currency": "INR",
              "Refund Amount": "Not Applicable", "Disbursement Type": "Refund", "Reversal Status": "Completed",
              "Website": "Amazon.in"}
    assert amazon.parse(_zip(tmp_path, [], [refund])) == []
