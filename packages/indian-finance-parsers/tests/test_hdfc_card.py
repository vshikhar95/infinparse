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


NET = [Txn(date(2026, 3, 5), D("-100.00"), "SHOP"), Txn(date(2026, 3, 6), D("-50.50"), "CAFE")]


def test_check_totals_ok_when_a_printed_pair_differs_by_net():
    hdfc.check_totals("Previous 1,000.00 Total Due 1,150.50", NET)


def test_check_totals_raises_when_nothing_reconciles():
    with pytest.raises(ValueError, match="reconcile"):
        hdfc.check_totals("Previous 1,000.00 Total Due 1,200.00", NET)


def test_check_totals_ignores_finance_charges():
    txns = NET + [Txn(date(2026, 3, 7), D("-10.00"), "FINANCE CHARGES")]
    hdfc.check_totals("Previous 1,000.00 Total Due 1,150.50", txns)


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
