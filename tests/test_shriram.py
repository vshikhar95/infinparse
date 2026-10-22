"""Shriram Finance FD receipts (deposit advice PDFs) -> one holding per deposit, as the receipt states it."""
from datetime import date
from decimal import Decimal as D

from indian_finance_parsers.portfolio import shriram

RECEIPT = """Name of Depositor : MR TEST PERSON Date of Issue : 01-01-2026
Customer ID : S0000001
We are pleased to issue this deposit Deposit No. TST-12345678 for Rs.500000.00. Thank you.
Customer ID S0000001 PAN ABCDE0000F Deposit No. TST-12345678 Scheme Cumulative
Date of Deposit Period (Months) Rate of Interest Maturity Amount (₹) Date of Maturity
7.00 % p.a. (on Cumulative basis)
01-01-2026 36 *612500.00 01-01-2029
Deposit Amount : ₹500000.00
"""


def test_deposit_as_the_receipt_states_it():
    h = shriram.holding_from_text(RECEIPT)
    assert (h.source, h.account, h.isin, h.as_of, h.units, h.price, h.value, h.matures) == (
        "shriram", "TST-12345678", "TST-12345678", date(2026, 1, 1), D(1), D("500000.00"), D("500000.00"), date(2029, 1, 1))


def test_name_carries_rate_and_maturity_amount():
    assert shriram.holding_from_text(RECEIPT).name == "Shriram FD TST-12345678 @ 7.00%, 612500.00 at maturity"


def test_parser_does_not_judge_maturity():
    import inspect
    assert "today" not in inspect.signature(shriram.holding_from_text).parameters


def test_not_a_receipt_raises():
    import pytest
    with pytest.raises(ValueError, match="not a Shriram FD receipt"):
        shriram.holding_from_text("some other pdf")
