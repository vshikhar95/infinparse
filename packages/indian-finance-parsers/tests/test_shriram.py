"""Shriram Finance FD receipts (deposit advice PDFs) -> one holding per deposit, as the receipt states it."""
from datetime import date
from decimal import Decimal as D

import pytest

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


def test_nominee_as_the_receipt_prints_it():
    assert shriram.holding_from_text(RECEIPT + "Nominee : TEST NOMINEE\n").nominee == "TEST NOMINEE"
    assert shriram.holding_from_text(RECEIPT + "Nominee : N.A.\n").nominee == "NA"  # receipt says there is none
    assert shriram.holding_from_text(RECEIPT).nominee == ""  # receipt doesn't say


FULL = """Customer ID S0000001 PAN ABCDE0000F Deposit No. TST-12345678 Scheme Cumulative
Date of Deposit Tenure (Months) Rate of Interest Maturity Amount (₹) Date of Maturity
7.00 % p.a.
01-01-2026 36 *612500.00 01-01-2029
Interest Frequency : Payable on Maturity
Deposit Amount : ₹500000.00
Nominee : TEST NOMINEE
"""


def test_deposit_terms_as_printed():
    d = shriram.deposit_from_text(FULL)
    assert (d.deposit_no, d.deposited, d.amount, d.rate, d.tenure_months, d.matures, d.maturity_amount) == (
        "TST-12345678", date(2026, 1, 1), D("500000.00"), D("7.00"), 36, date(2029, 1, 1), D("612500.00"))
    assert (d.scheme, d.interest_payout, d.nominee) == ("Cumulative", "Payable on Maturity", "TEST NOMINEE")


def test_deposit_without_the_optional_lines():
    d = shriram.deposit_from_text(RECEIPT)  # no payout line, no nominee
    assert (d.interest_payout, d.nominee) == ("", "") and d.rate == D("7.00")


def test_holding_from_text_is_unchanged():
    assert shriram.holding_from_text(FULL).name == "Shriram FD TST-12345678 @ 7.00%, 612500.00 at maturity"


@pytest.mark.parametrize("old,new,field", [("612500.00", "400000.00", "maturity_amount"), ("01-01-2029", "01-01-2025", "matures"),
                                           (" 36 ", " 60 ", "tenure_months")])
def test_contradicting_receipt_raises_naming_file_and_field(old, new, field):
    with pytest.raises(ValueError, match=f"^r.pdf: {field} is inconsistent") as e:
        shriram.deposit_from_text(FULL.replace(old, new), "r.pdf")
    assert "400000" not in str(e.value)


def test_tenure_must_match_the_dates_within_a_few_days():
    shriram.deposit_from_text(FULL.replace("01-01-2029", "03-01-2029"))
    with pytest.raises(ValueError, match="tenure_months is inconsistent"):
        shriram.deposit_from_text(FULL.replace("01-01-2029", "20-01-2029"))


def test_scheme_naming_cumulative_among_other_words_still_needs_a_bigger_maturity_amount():
    with pytest.raises(ValueError, match="maturity_amount is inconsistent"):
        shriram.deposit_from_text(FULL.replace("Scheme Cumulative", "Scheme Unnati Cumulative").replace("*612500.00", "*500000.00"))
    shriram.deposit_from_text(FULL.replace("Scheme Cumulative", "Scheme Non Cumulative").replace("*612500.00", "*500000.00"))


def test_non_cumulative_needs_no_bigger_maturity_amount():
    shriram.deposit_from_text(FULL.replace("Cumulative\n", "Non-Cumulative\n", 1).replace("*612500.00", "*500000.00"))


def _pdf(tmp_path, text):
    from fpdf import FPDF
    pdf = FPDF(unit="pt", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", size=9)
    for i, line in enumerate(text.replace("₹", "").splitlines()):  # the core font has no rupee sign; the sign is optional
        pdf.text(20, 30 + 14 * i, line)
    path = tmp_path / "receipt.pdf"
    pdf.output(str(path))
    return path


def test_deposits_reads_a_pdf_and_names_the_file_on_failure(tmp_path):
    assert shriram.deposits(_pdf(tmp_path, FULL))[0].deposit_no == "TST-12345678"
    with pytest.raises(ValueError, match="^receipt.pdf: matures is inconsistent"):
        shriram.deposits(_pdf(tmp_path, FULL.replace("01-01-2029", "01-01-2025")))
    with pytest.raises(ValueError, match="^receipt.pdf: not a Shriram FD receipt"):
        shriram.deposits(_pdf(tmp_path, "some other pdf"))


def test_payout_mid_line_is_read():
    assert shriram.deposit_from_text(FULL.replace("Interest Frequency :", "Branch:XX Interest Frequency :")).interest_payout == "Payable on Maturity"


def test_unreadable_dates_raise_without_the_value():
    for fn in (shriram.deposit_from_text, shriram.holding_from_text):
        with pytest.raises(ValueError) as e:
            fn(FULL.replace("01-01-2029", "99-99-2029"), "r.pdf")
        assert str(e.value) == "r.pdf: maturity date is unreadable"


def test_other_interest_lines_are_not_the_payout():
    t = FULL.replace("Interest Frequency : Payable on Maturity", "Interest Rate : 7.00 %\nInterest Amount : 112500.00\nInterest Component : 5")
    assert shriram.deposit_from_text(t).interest_payout == "5"  # a 9-letter label is accepted; Rate and Amount are not
    assert shriram.deposit_from_text(t.replace("Interest Component : 5", "")).interest_payout == ""
