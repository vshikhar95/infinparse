"""Bajaj Finance FD receipts -> a Holding (parse) and a Deposit (deposits), as the receipt states them."""
from datetime import date
from decimal import Decimal as D

import pytest

from indian_finance_parsers.portfolio import bajaj_fd

RECEIPT = """Bajaj Finance Limited Fixed Deposit Receipt
DEPOSIT NUMBER: 1234567 REF NO.: TST NO.: 1*
Maturity amount*
Deposit date Scheme type Deposit period (Months) Maturity date Interest rate (P.A.) Deposit amount (Rs.) Interest amount (Rs.)
(Rs.)
01-01-2026 Cumulative 12M 0D 01-01-2027 7.00% 1,00,000.00 7,000.00 1,07,000.00
FD Details Nominee Details
Interest Payment Frequency : OnMaturity
Nominee 1 : TEST NOMINEE ONE
Nominee 2 : TEST NOMINEE TWO
Nominee 3 :
"""


def test_deposit_terms_as_printed():
    d = bajaj_fd.deposit_from_text(RECEIPT)
    assert (d.deposit_no, d.deposited, d.amount, d.rate, d.tenure_months, d.matures, d.maturity_amount) == (
        "1234567", date(2026, 1, 1), D("100000.00"), D("7.00"), 12, date(2027, 1, 1), D("107000.00"))
    assert (d.scheme, d.interest_payout, d.nominee) == ("Cumulative", "OnMaturity", "TEST NOMINEE ONE; TEST NOMINEE TWO")


def test_holding_mirrors_shriram():
    h = bajaj_fd.holding_from_text(RECEIPT)
    assert (h.source, h.account, h.isin, h.as_of, h.units, h.price, h.value, h.matures, h.nominee) == (
        "bajaj", "1234567", "1234567", date(2026, 1, 1), D(1), D("100000.00"), D("100000.00"), date(2027, 1, 1),
        "TEST NOMINEE ONE; TEST NOMINEE TWO")
    assert h.name == "Bajaj Finance FD 1234567 @ 7.00%, 107000.00 at maturity"


def test_no_nominee_slots_filled_reads_empty():
    assert bajaj_fd.deposit_from_text(RECEIPT.split("Nominee 1")[0]).nominee == ""


def test_not_a_bajaj_receipt_raises():
    for text in ("some other pdf", RECEIPT.replace("Bajaj Finance", "Other"), RECEIPT.replace("DEPOSIT NUMBER", "NUMBER")):
        with pytest.raises(ValueError, match="not a Bajaj Finance FD receipt"):
            bajaj_fd.deposit_from_text(text)


@pytest.mark.parametrize("old,new,field", [("1,07,000.00", "1,09,000.00", "maturity_amount"), ("01-01-2027", "01-01-2025", "matures"),
                                           ("12M", "36M", "tenure_months")])
def test_contradicting_receipt_raises_naming_file_and_field(old, new, field):
    with pytest.raises(ValueError, match=f"^r.pdf: {field}") as e:
        bajaj_fd.deposit_from_text(RECEIPT.replace(old, new), "r.pdf")
    assert "109" not in str(e.value) and "107" not in str(e.value)


def test_parse_and_deposits_read_a_pdf_and_name_the_file(tmp_path):
    from fpdf import FPDF
    pdf = FPDF(unit="pt", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", size=8)
    for i, line in enumerate(RECEIPT.splitlines()):
        pdf.text(10, 30 + 12 * i, line)
    p = tmp_path / "fd.pdf"
    pdf.output(str(p))
    assert bajaj_fd.parse(p)[0].account == "1234567" and bajaj_fd.deposits(p)[0].tenure_months == 12
    pdf = FPDF(unit="pt", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", size=8)
    pdf.text(10, 30, "some other pdf")
    q = tmp_path / "other.pdf"
    pdf.output(str(q))
    with pytest.raises(ValueError, match="^other.pdf: not a Bajaj Finance FD receipt"):
        bajaj_fd.parse(q)
