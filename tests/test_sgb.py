"""Sovereign Gold Bond: RBI certificate -> holding at cost; revalued per gram at the IBJA 999 rate (RBI's redemption basis)."""
from datetime import date
from decimal import Decimal as D

import pytest

from indian_finance_parsers.portfolio import sgb

CERT = """Reserve Bank of India Print Date 20-Mar-2024
Issue Reference 2024 / 99999
Security Code IN0020249999 12345 - SGB 2099-00 SERIES IX
Subscription Date 08-MAR-2024 Settlement Date 15-MAR-2024
Number of Units 5 Issue Price 5000
(In Grams)
Consideration Amount ` 25,000.00
Maturity Date 15-MAR-2032"""


def test_certificate_becomes_a_holding_at_cost():
    h = sgb.holding_from_text(CERT, owner="own")
    assert (h.as_of, h.source, h.account, h.isin, h.units, h.price, h.value, h.owner) == (
        date(2024, 3, 15), "sgb", "IN0020249999", "IN0020249999", D(5), D(5000), D(25000), "own")
    assert h.name == "SGB 2099-00 SERIES IX (matures 2032-03-15)"


def test_not_a_certificate_raises():
    with pytest.raises(ValueError, match="not an RBI SGB certificate"):
        sgb.holding_from_text("some other pdf", owner="own")


def test_ibja_999_rate_is_per_gram_from_the_pm_rate_per_10g():
    html = '<span id="lblGold999_AM">100000</span><span id="lblGold999_PM">100100</span>'
    assert sgb.ibja_999(html) == D("10010")


def test_revalue_writes_a_snapshot_dated_today_at_the_new_price():
    h = sgb.holding_from_text(CERT, owner="own")
    v = sgb.revalue(h, D("10010"), date(2026, 10, 21))
    assert (v.as_of, v.price, v.value, v.units, v.account) == (date(2026, 10, 21), D("10010"), D("50050"), D(5), h.account)


def test_revalue_accepts_units_as_stored_in_the_db():
    from dataclasses import replace
    h = replace(sgb.holding_from_text(CERT, owner="own"), units="5")  # sqlite hands back text
    assert sgb.revalue(h, D("100"), date(2026, 1, 1)).value == D(500)


def test_fetch_rate_sends_a_neutral_user_agent(monkeypatch):
    import io
    seen = {}

    def fake_urlopen(req, timeout):
        seen["ua"] = req.get_header("User-agent")
        return io.BytesIO(b'<span id="lblGold999_AM">100000</span>')
    monkeypatch.setattr(sgb.urllib.request, "urlopen", fake_urlopen)
    assert sgb.fetch_rate() == D(10000)
    assert seen["ua"].startswith("indian-finance-parsers")
