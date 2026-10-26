"""Tests for the ICICI foreign-refund summary check and the HDFC year-end refusal."""
from decimal import Decimal as D
from pathlib import Path

import pytest

from indian_finance_parsers.importers import hdfc_card, icici_card_pdf as icici

FIX = Path(__file__).parent / "fixtures"
LINES = (FIX / "icici_card_pdf_foreign_refund_lines.txt").read_text().splitlines()
ROWS = icici.rows_from_lines(LINES)
FX = icici.foreign_refs(LINES)
# rows: debits 6,050.00, credits 5,000.00. The foreign refund prints net of forex markup (3.5% + 18% GST = 4.13%):
# gross 1,041.30, markup 41.30 -> the summary counts 41.30 more in Payments/Credits AND in Purchases/Charges.


def summary(purchases, credits):
    return [D("0"), D(purchases), D("0"), D(credits)]


def check(summ, rows=ROWS, fx=FX):
    icici.check_summary(summ, rows, "x.pdf", fx)


def test_foreign_refund_markup_shortfall_on_both_sides_passes():
    check(summary("6091.30", "5041.30"))


def test_shortfall_on_one_side_only_still_raises():
    with pytest.raises(ValueError, match="parsed"):
        check(summary("6050.00", "5041.30"))


def test_equal_shortfall_without_a_foreign_refund_raises():
    domestic = [r for r in ROWS if r.ref != "12345678904"]
    with pytest.raises(ValueError, match="parsed"):
        check(summary("6091.30", "4041.30"), domestic, icici.foreign_refs([l for ln in LINES if "12345678904" not in ln]))


def test_decimal_foreign_amount_is_still_recognised():
    lines = [ln.replace("10 USD", "10.00 USD") for ln in LINES]
    rows = icici.rows_from_lines(lines)
    assert "USD" not in rows[-1].description  # the parser strips a decimal foreign amount from the description
    check(summary("6091.30", "5041.30"), rows, icici.foreign_refs(lines))


def test_shortfall_larger_than_the_markup_raises():
    with pytest.raises(ValueError, match="parsed"):
        check(summary("6200.00", "5150.00"))


def test_year_end_statement_is_refused_not_misread(monkeypatch):
    text = (FIX / "hdfc_card_year_end_page0.txt").read_text()

    class Page:
        def extract_text(self):
            return text

    class Pdf:
        pages = [Page()]
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

    monkeypatch.setattr(hdfc_card.pdfplumber, "open", lambda path: Pdf())
    with pytest.raises(ValueError, match="annual year-end summary"):
        hdfc_card.parse("x-FY2024-2025.pdf")
