"""Sovereign Gold Bond: RBI certificate -> one holding at cost, with its maturity date."""
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
    h = sgb.holding_from_text(CERT)
    assert (h.as_of, h.source, h.account, h.isin, h.units, h.price, h.value, h.matures) == (
        date(2024, 3, 15), "sgb", "IN0020249999", "IN0020249999", D(5), D(5000), D(25000), date(2032, 3, 15))
    assert h.name == "SGB 2099-00 SERIES IX"


def test_not_a_certificate_raises():
    with pytest.raises(ValueError, match="not an RBI SGB certificate"):
        sgb.holding_from_text("some other pdf")


def test_no_network_helpers():
    assert not hasattr(sgb, "fetch_rate")  # valuation needs the network; it's the caller's job
