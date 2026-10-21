"""Shriram Finance FD receipts (deposit advice PDFs) -> one holding per deposit."""
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


def test_receipt_fields_are_read():
    fd = shriram.fd_from_text(RECEIPT)
    assert fd == {"deposit_no": "TST-12345678", "deposited": date(2026, 1, 1), "amount": D("500000.00"),
                  "rate": D("7.00"), "matures": date(2029, 1, 1), "maturity_amount": D("612500.00")}


def test_open_fd_counts_at_deposit_amount():
    [h] = shriram.holdings_from_text(RECEIPT, today=date(2026, 10, 21), owner="unconfirmed")
    assert (h.source, h.account, h.value, h.as_of, h.owner) == ("shriram", "TST-12345678", D("500000.00"),
                                                                 date(2026, 1, 1), "unconfirmed")


def test_matured_fd_counts_zero_as_of_maturity():
    [h] = shriram.holdings_from_text(RECEIPT, today=date(2029, 11, 1), owner="unconfirmed")
    assert (h.value, h.as_of) == (D("0"), date(2029, 1, 1))


def test_holding_name_carries_rate_maturity_date_and_amount():
    [h] = shriram.holdings_from_text(RECEIPT, today=date(2026, 10, 21), owner="unconfirmed")
    assert h.name == "Shriram FD TST-12345678 @ 7.00% to 2029-01-01, 612500.00 at maturity"
