"""Humble Bundle order export (humble_orders.json from the /api/v1/order endpoints, gamekeys hashed)."""
from datetime import date
from decimal import Decimal as D
from pathlib import Path

from purchase_history_parsers import humble

FIXTURE = Path(__file__).parent / "fixtures" / "humble_orders.json"


def by_id():
    return {p.order_id: p for p in humble.parse(FIXTURE)}


def test_paid_order_is_a_purchase_with_amount_currency_and_date():
    p = by_id()["aaaa000000000002"]
    assert (p.store, p.kind, p.amount, p.currency, p.date) == ("humble", "purchase", D("12.49"), "USD", date(2024, 3, 1))


def test_items_name_the_bundle_then_its_games():
    assert by_id()["aaaa000000000001"].items == "Humble Test Bundle: Game One | Game Two"


def test_free_and_gifted_orders_are_kept_but_not_purchases():
    ps = by_id()
    assert (ps["aaaa000000000003"].kind, ps["aaaa000000000004"].kind) == ("other", "other")
    assert ps["aaaa000000000004"].raw_type == "gift received"


def test_inr_orders_keep_their_currency():
    assert (by_id()["aaaa000000000005"].currency, by_id()["aaaa000000000005"].amount) == ("INR", D("899"))


def test_free_order_without_currency_is_kept_with_empty_currency():
    p = by_id()["aaaa000000000006"]
    assert (p.kind, p.currency, p.items) == ("other", "", "Old Freebie")
