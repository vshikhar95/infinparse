from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest

from indian_finance_parsers.importers import icici_card_pdf as icici

LINES = (Path(__file__).parent / "fixtures" / "icici_card_pdf_lines.txt").read_text().splitlines()


@pytest.fixture(scope="module")
def rows():
    return icici.rows_from_lines(LINES)


def test_non_row_lines_are_skipped(rows):
    assert len(rows) == 5


def test_row_with_points(rows):
    assert (rows[0].date, rows[0].amount, rows[0].description) == (date(2026, 3, 5), D("-1234.56"), "ACME STORE TESTCITY IN")


def test_row_without_points(rows):
    assert (rows[1].amount, rows[1].description) == (D("-450.00"), "BOOKS ONLINE SAMPLEPUR IN")


def test_foreign_amount_and_currency_dropped(rows):
    assert (rows[2].amount, rows[2].description) == (D("-1050.00"), "GLOBEX LTD LONDON GB")


def test_cr_is_credit(rows):
    assert rows[3].amount == D("5000.00")


def test_card_section_sets_notes_for_following_rows_only(rows):
    assert [r.notes for r in rows] == ["", "", "", "", "card 4111 XXXX XXXX 2222"]


def test_check_totals_ok(rows):
    icici.check_summary([D("0"), D("2833.56"), D("0"), D("5000.00")], rows)


def test_check_totals_debit_mismatch(rows):
    with pytest.raises(ValueError, match="parsed debits don't match"):
        icici.check_summary([D("0"), D("2833.55"), D("0"), D("5000.00")], rows)


def test_check_totals_cash_advance_counts_as_debit(rows):
    icici.check_summary([D("0"), D("2000.00"), D("833.56"), D("5000.00")], rows)
