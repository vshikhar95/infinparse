from datetime import date
from decimal import Decimal as D
from pathlib import Path

from purchase_history_parsers import google_play

FIX = Path(__file__).parent / "fixtures"


def test_google_play_titles_refund_and_stable_ids():
    a = google_play.parse(FIX / "google_play.html")
    assert [(p.items, p.amount, p.refunded, p.raw_type) for p in a] == [
        ("Fake Game Pass", D("1299.00"), False, ""),
        ("Demo App Pro", D("99.00"), True, "Refunded"),
        ("Fake Game Pass", D("1299.00"), False, ""),
    ]
    assert a[0].date == date(2026, 10, 1) and a[1].date == date(2026, 9, 19)
    assert {p.kind for p in a} == {"purchase"} and {p.currency for p in a} == {"INR"}
    ids = [p.order_id for p in a]
    assert len(set(ids)) == 3  # repeat renewal on a different date stays distinct
    assert [p.order_id for p in google_play.parse(FIX / "google_play.html")] == ids


def test_google_play_repeat_same_day_gets_distinct_ids(tmp_path):
    block = '<div>Fake Game Pass</div><div>1 Oct 2026</div><div>₹10.00</div>'
    p = tmp_path / "gp.html"
    p.write_text(f"<html><body><h1>Order history</h1>{block}{block}</body></html>")
    ids = [x.order_id for x in google_play.parse(p)]
    assert len(ids) == 2 and ids[0] != ids[1]
