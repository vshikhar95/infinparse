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


NOMINEES = """
Nominee Details
Sr No Nominee ID Nominee Name
1 TEST NOMINEE ONE
2 TEST NOMINEE TWO
Some footer"""


def test_cost_is_the_consideration_amount_printed_and_value_stays_units_times_price():
    h = sgb.holding_from_text(CERT.replace("5000", "5100", 1))  # issue price 5100: value 25,500, paid 25,000
    assert (h.cost, h.value) == (D("25000.00"), D(25500))
    assert sgb.holding_from_text(CERT.replace("Consideration Amount ` 25,000.00\n", "")).cost is None


def test_nominees_are_joined_and_absent_section_reads_empty():
    assert sgb.holding_from_text(CERT + NOMINEES).nominee == "TEST NOMINEE ONE; TEST NOMINEE TWO"
    assert sgb.holding_from_text(CERT).nominee == ""
    assert sgb.holding_from_text(CERT + "\nNominee Details\nSr No Nominee ID Nominee Name\n").nominee == ""
