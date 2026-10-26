import json
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest
from indian_finance_parsers.importers import sbi_card as sbi

WORDS = json.loads((Path(__file__).parent / "fixtures" / "sbi_card_words.json").read_text())


@pytest.fixture(scope="module")
def rows():
    return sbi.rows_from_words(WORDS)


def test_zero_amount_memo_row_skipped(rows):
    assert len(rows) == 2


def test_wrapped_description_above_and_below_joined_in_reading_order(rows):
    assert (rows[0].date, rows[0].amount, rows[0].description) == (date(2026, 3, 5), D("-1200.00"), "WRAPPED SHOP ONE CONT")


def test_fragment_goes_to_nearest_row(rows):
    assert (rows[1].amount, rows[1].description) == (D("300.00"), "CAFE MORE")


def test_rs_header_fragment_in_amount_column_ignored(rows):
    assert all("Rs.)" not in r.description and r.amount != 0 for r in rows)


def test_rows_above_header_not_anchors(rows):
    assert date(2026, 3, 1) not in [r.date for r in rows]


def test_no_anchors_gives_no_rows():
    assert sbi.rows_from_words([w for w in WORDS if w["top"] < 105]) == []


def test_unknown_type_raises():
    words = [dict(w, text="Refund") if w["text"] == "Debit" else w for w in WORDS]
    with pytest.raises(ValueError, match="unexpected type"):
        sbi.rows_from_words(words)
