import json
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest

from indian_finance_parsers.importers import hdfc_card as hdfc
from indian_finance_parsers.models import Txn


def w(text, x):
    return {"text": text, "x0": x}

ROWS = json.loads((Path(__file__).parent / "fixtures" / "hdfc_card_rows.json").read_text())


@pytest.fixture(scope="module")
def rows():
    return hdfc.rows_from_words(ROWS, coins_x=420)


def test_only_dated_timed_amount_rows_kept(rows):
    assert len(rows) == 5


def test_old_format_debit_drops_neucoins_column(rows):
    assert (rows[0].date, rows[0].amount, rows[0].description) == (date(2026, 3, 5), D("-1234.56"), "ACME STORE")


def test_neucoins_plus_is_not_a_credit(rows):
    assert (rows[1].amount, rows[1].description) == (D("-250.00"), "CAFE TEST")


def test_new_format_plus_rupee_is_credit(rows):
    assert (rows[2].amount, rows[2].description) == (D("500.00"), "REFUND SHOP")


def test_trailing_glyph_ignored(rows):
    assert (rows[3].amount, rows[3].description) == (D("-300.00"), "BOOKSTORE")


def test_cr_suffix_is_credit(rows):
    assert (rows[4].amount, rows[4].description) == (D("5000.00"), "PAYMENT RECEIVED")


def test_without_coins_x_neucoins_number_stays_in_description():
    assert hdfc.rows_from_words(ROWS, coins_x=None)[0].description == "ACME STORE 12"


def test_description_wrapped_above_and_below_a_bare_payment_row_is_kept():
    rows = [[w("BPPY", 120), w("CC", 150), w("PAYMENT", 170), w("(Ref#", 230)],
            [w("03/09/2026|", 20), w("10:00", 80), w("+", 380), w("C", 390), w("12,000.00", 400), w("l", 460)],
            [w("ST0000001)", 120)],
            [w("04/09/2026|", 20), w("10:00", 80), w("SHOP", 120), w("C", 390), w("99.00", 400)]]
    assert [(t.amount, t.description) for t in hdfc.rows_from_words(rows, coins_x=None)] == [
        (D("12000.00"), "BPPY CC PAYMENT (Ref# ST0000001)"), (D("-99.00"), "SHOP")]


def test_emi_eligible_marker_is_stripped_and_noted():
    # HDFC prints "EMI " before any charge that may be converted to EMI; it is still an ordinary charge
    rows = [[w("04/09/2026|", 20), w("10:00", 80), w("EMI", 120), w("TESTMART", 150), w("CITY", 210),
             w("C", 390), w("2,518.24", 400)],
            [w("05/09/2026|", 20), w("10:00", 80), w("SHOP", 120), w("C", 390), w("99.00", 400)]]
    assert [(t.amount, t.description, t.notes) for t in hdfc.rows_from_words(rows, coins_x=None)] == [
        (D("-2518.24"), "TESTMART CITY", "EMI eligible"), (D("-99.00"), "SHOP", "")]


def test_a_lone_emi_word_is_not_a_marker():
    rows = [[w("04/09/2026|", 20), w("10:00", 80), w("EMI", 120), w("C", 390), w("50.00", 400)]]
    assert [(t.description, t.notes) for t in hdfc.rows_from_words(rows, coins_x=None)] == [("EMI", "")]


def test_credit_rows_without_a_time_are_kept():
    # older layout: payments and refunds print no time column and glue "Cr" to the amount
    rows = [[w("01/06/2024", 20), w("TELE", 80), w("TRANSFER", 110), w("CREDIT", 150), w("(Ref#", 190),
             w("XX0000000000)", 220), w("12,000.00Cr", 400)],
            [w("02/06/2024", 20), w("10:00:00", 80), w("SHOP", 120), w("500.00", 400)]]
    assert [(t.amount, t.description) for t in hdfc.rows_from_words(rows, coins_x=None)] == [
        (D("12000.00"), "TELE TRANSFER CREDIT (Ref# XX0000000000)"), (D("-500.00"), "SHOP")]


def _box(labels, amounts, top=200):
    """Summary-box words: labels on one row, amounts (left to right) a little below."""
    return ([{"text": t, "x0": x, "top": top} for t, x in labels]
            + [{"text": a, "x0": 60 + 100 * i, "top": top + 25 + (i == 1) * -5} for i, a in enumerate(amounts)])


OLD_LABELS = [("Opening", 60), ("Payment/", 160), ("Purchase/", 260), ("Finance", 360), ("Total", 460)]
NEW_LABELS = [("PREVIOUS", 60), ("FINANCE", 360), ("TOTAL", 460)]


def test_summary_box_is_read_in_both_layouts():
    old = hdfc.summary_from_words(_box(OLD_LABELS, ["1,000.00", "12,000.00", "12,500.00", "10.00", "1,510.00"]))
    new = hdfc.summary_from_words(_box(NEW_LABELS, ["C1,000.00", "C12,000.00", "C12,500.00", "C10.00", "C1,510.00"]))
    assert old == new == {"opening": D("1000.00"), "credits": D("12000.00"), "debits": D("12500.00"),
                          "charges": D("10.00"), "total": D("1510.00")}


def test_summary_box_that_doesnt_add_up_is_not_trusted():
    assert hdfc.summary_from_words(_box(OLD_LABELS, ["1,000.00", "12,000.00", "12,500.00", "10.00", "9,999.00"])) is None


SUMMARY = {"opening": D("1000.00"), "credits": D("12000.00"), "debits": D("12500.00"), "charges": D("10.00"),
           "total": D("1510.00")}
SUMMARY_ROWS = [Txn(date(2024, 6, 1), D("12000.00"), "TELE TRANSFER CREDIT"), Txn(date(2024, 6, 2), D("-12500.00"), "SHOP"),
        Txn(date(2024, 6, 3), D("-10.00"), "FINANCE CHARGES")]


def test_rows_matching_the_summary_pass():
    hdfc.check_summary(SUMMARY, SUMMARY_ROWS, "s.PDF")
    hdfc.check_summary(SUMMARY, SUMMARY_ROWS[:2], "s.PDF")  # finance charges printed only in the box


def test_a_dropped_payment_rejects_the_file_without_amounts():
    with pytest.raises(ValueError, match="^s.PDF: parsed credits don't match") as e:
        hdfc.check_summary(SUMMARY, SUMMARY_ROWS[1:], "s.PDF")
    assert "12" not in str(e.value)


def test_a_dropped_purchase_rejects_the_file():
    with pytest.raises(ValueError, match="debits don't match"):
        hdfc.check_summary(SUMMARY, [SUMMARY_ROWS[0]], "s.PDF")


def test_the_due_date_line_is_not_a_transaction():
    # the header prints "<due date> <total due> <minimum due>": dated, but no time and no Cr, so not a row
    rows = [[w("15/06/2024", 300), w("13,316.00", 380), w("666.00", 460)]]
    assert hdfc.rows_from_words(rows, coins_x=None) == []
