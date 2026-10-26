"""PlayStation Store purchase-receipt emails (saved as HTML)."""
from datetime import date
from decimal import Decimal as D
from pathlib import Path

from purchase_history_parsers import playstation

FIX = Path(__file__).parent / "fixtures" / "psn"


def one(name):
    [p] = playstation.parse(FIX / name)
    return p


def test_paid_order_has_number_date_total_and_items():
    p = one("paid_card.html")
    assert (p.store, p.order_id, p.date, p.amount, p.currency, p.kind) == (
        "playstation", "111111111111111", date(2026, 9, 5), D(999), "INR", "purchase")
    assert p.items == "Fake Quest Deluxe PS4 & PS5 (Game) | Fake Quest Soundtrack (Add-on)"


def test_card_fund_source_is_recorded_and_is_what_was_charged():
    p = one("paid_card.html")
    assert (p.payment, p.charged) == ("MasterCard 4111…1111", D(999))


def test_subscription_recurring_fee_note_is_not_an_item():
    p = one("subscription.html")
    assert p.items == "PlayStation Plus Deluxe: 12 Month Subscription (Subscription)"
    assert (p.amount, p.payment) == (D(1000), "VISA 4111…2222")


def test_zero_rupee_order_is_flagged_free_not_a_purchase():
    p = one("free.html")
    assert (p.kind, p.amount, p.raw_type) == ("other", D(0), "free (likely PS Plus)")


def test_older_receipt_layout_parses_date_and_items():
    p = one("old_format.html")
    assert (p.order_id, p.date, p.items, p.kind) == ("444444444444", date(2022, 1, 3), "Fake Studio Tool (Game)", "other")
