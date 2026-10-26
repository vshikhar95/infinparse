"""Blinkit order export (blinkit-orders.PERSONAL.json from the browser exporter)."""
from datetime import date
from decimal import Decimal as D
from pathlib import Path

from purchase_history_parsers import blinkit

FIXTURE = Path(__file__).parent / "fixtures" / "blinkit_orders.json"


def by_id():
    return {p.order_id: p for p in blinkit.parse(FIXTURE)}


def test_delivered_order_is_a_purchase_with_total_date_and_items():
    p = by_id()["ORD1000000001"]
    assert (p.store, p.kind, p.amount, p.currency, p.date, p.raw_type) == (
        "blinkit", "purchase", D(150), "INR", date(2024, 3, 1), "DELIVERED")
    assert p.items == "Test Milk 500ml | Test Bread ×2"


def test_cancelled_and_null_total_orders_are_other():
    ps = by_id()
    assert (ps["ORD1000000002"].kind, ps["ORD1000000002"].raw_type) == ("other", "CANCELLED")
    assert (ps["ORD1000000003"].kind, ps["ORD1000000003"].amount) == ("other", D(0))


def test_order_without_a_date_is_skipped():
    assert "ORD1000000004" not in by_id()


def test_card_digits_never_reach_payment():
    ps = by_id()
    assert (ps["ORD1000000001"].payment, ps["ORD1000000005"].payment, ps["ORD1000000002"].payment) == ("Card", "Card", "UPI")


def test_ids_are_stable_across_reparses():
    assert [p.order_id for p in blinkit.parse(FIXTURE)] == [p.order_id for p in blinkit.parse(FIXTURE)]
