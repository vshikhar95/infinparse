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


def _page(*items):
    """Words (text, x0, top) with x1 estimated from the text, placed as in the real page 0."""
    return [{"text": t, "x0": x, "x1": x + 6 * len(t), "top": top} for t, x, top in items]


# 2025+ layout, invented values, label and figure positions as printed
NEW_PAGE = _page(
    ("Statement", 193, 120.2), ("Date", 224, 120.2), ("05", 340, 120.2), ("Jan,", 349, 120.2), ("2031", 362, 120.2),
    ("Billing", 193, 134.9), ("Period", 211, 134.9), ("06", 298, 134.9), ("Dec,", 307, 134.9), ("2030", 321, 134.9),
    ("-", 337, 134.9), ("05", 340, 134.9), ("Jan,", 349, 134.9), ("2031", 362, 134.9),
    ("PREVIOUS", 39, 219.5), ("STATEMENT", 71, 219.5), ("DUES", 108, 219.5),
    ("TOTAL", 445, 220.1), ("AMOUNT", 466, 220.1), ("DUE", 495, 220.1), ("C1,510.00", 445, 235.2),
    ("C1,000.00", 63, 242.2), ("C12,000.00", 167, 242.2), ("C12,500.00", 267, 242.2), ("C10.00", 371, 242.2),
    ("TOTAL", 64, 266.9), ("CREDIT", 85, 266.9), ("LIMIT", 107, 266.9), ("(Including", 71, 275.4), ("Cash)", 101, 275.4),
    ("AVAILABLE", 182, 271.2), ("CREDIT", 216, 271.2), ("LIMIT", 238, 271.2),
    ("AVAILABLE", 317, 271.2), ("CASH", 351, 271.2), ("LIMIT", 368, 271.2),
    ("MINIMUM", 445, 272.9), ("DUE", 478, 272.9), ("DUE", 512, 272.9), ("DATE", 526, 272.9),
    ("C150.00", 445, 289.7), ("25", 512, 289.7), ("Jan,", 522, 289.7), ("2031", 537, 289.7),
    ("C5,00,000", 77, 293.8), ("C4,00,000", 202, 293.8), ("C80,000", 338, 293.8))

# 2024 layout
OLD_PAGE = _page(
    ("Statement", 252, 73.9), ("Date:05/01/2030", 293, 73.9),
    ("Payment", 267, 95.9), ("Due", 303, 95.9), ("Date", 321, 95.9), ("Total", 396, 95.9), ("Dues", 418, 95.9),
    ("Minimum", 488, 95.9), ("Amount", 525, 95.9), ("Due", 557, 95.9),
    ("25/01/2030", 284, 117.3), ("1,510.00", 401, 117.3), ("150.00", 519, 117.3),
    ("Credit", 281, 139.4), ("Limit", 306, 139.4), ("Available", 376, 139.4), ("Credit", 413, 139.4),
    ("Limit", 439, 139.4), ("Available", 491, 139.4), ("Cash", 528, 139.4), ("Limit", 550, 139.4),
    ("5,00,000", 289, 161.3), ("4,00,000", 403, 161.3), ("80,000", 519, 161.3),
    ("Opening", 264, 200.4), ("Payment/", 329, 200.4), ("Purchase/", 396, 200.4), ("Finance", 469, 200.4),
    ("Total", 532, 205.4), ("Dues", 554, 205.4),
    ("1,000.00", 267, 230.3), ("12,000.00", 333, 230.3), ("12,500.00", 401, 230.3), ("10.00", 478, 230.3),
    ("1,510.00", 537, 230.3))


@pytest.mark.parametrize("page", [NEW_PAGE, OLD_PAGE])
def test_card_summary_in_both_layouts(page):
    s = hdfc.card_summary(page, "s.PDF")
    assert (s.total_due, s.minimum_due, s.previous_balance, s.payments, s.purchases, s.charges) == (
        D("1510.00"), D("150.00"), D("1000.00"), D("12000.00"), D("12500.00"), D("10.00"))
    assert (s.credit_limit, s.available_credit, s.cash_limit, s.available_cash) == (
        D(500000), D(400000), None, D(80000)) if page is NEW_PAGE else (D(500000), D(400000), None, D(80000))
    assert (s.statement_date, s.due_date) == (date(2031, 1, 5), date(2031, 1, 25)) if page is NEW_PAGE else (
        date(2030, 1, 5), date(2030, 1, 25))


def test_card_summary_period_only_in_the_new_layout():
    s = hdfc.card_summary(NEW_PAGE, "s.PDF")
    assert (s.period_start, s.period_end) == (date(2030, 12, 6), date(2031, 1, 5))
    assert hdfc.card_summary(OLD_PAGE, "s.PDF").period_start is None


def _without(page, text):
    return [w for w in page if w["text"] != text]


@pytest.mark.parametrize("page,text,field", [(NEW_PAGE, "C80,000", "available_cash"), (OLD_PAGE, "25/01/2030", "due_date"),
                                             (OLD_PAGE, "Date:05/01/2030", "statement_date")])
def test_a_missing_figure_raises_naming_file_and_field(page, text, field):
    with pytest.raises(ValueError, match=f"^s.PDF: {field} not found"):
        hdfc.card_summary(_without(page, text), "s.PDF")


def _swap(page, old, new):
    return [dict(w, text=new) if w["text"] == old else w for w in page]


@pytest.mark.parametrize("old,new,field", [("150.00", "9,150.00", "minimum_due"), ("4,00,000", "9,00,000", "available_credit"),
                                           ("25/01/2030", "04/01/2030", "due_date")])
def test_inconsistent_figures_raise_without_amounts(old, new, field):
    with pytest.raises(ValueError, match=f"^s.PDF: {field} is inconsistent") as e:
        hdfc.card_summary(_swap(OLD_PAGE, old, new), "s.PDF")
    assert "150" not in str(e.value)


def test_a_box_that_doesnt_add_up_raises():
    with pytest.raises(ValueError, match="^s.PDF: statement summary box"):
        hdfc.card_summary(_swap(OLD_PAGE, "12,500.00", "99.00"), "s.PDF")


@pytest.mark.parametrize("page,old,new,field", [(OLD_PAGE, "25/01/2030", "99/99/2030", "due_date"),
                                                (OLD_PAGE, "Date:05/01/2030", "Date:99/99/2030", "statement_date"),
                                                (NEW_PAGE, "Jan,", "Xyz,", "statement_date")])
def test_a_malformed_date_raises_without_the_value(page, old, new, field):
    with pytest.raises(ValueError) as e:
        hdfc.card_summary(_swap(page, old, new), "s.PDF")
    assert str(e.value) in (f"s.PDF: {field} is unreadable", f"s.PDF: {field} not found") and "99" not in str(e.value)


def test_a_comma_only_figure_is_not_an_amount():
    with pytest.raises(ValueError, match="^s.PDF: credit_limit not found"):
        hdfc.card_summary(_swap(OLD_PAGE, "5,00,000", "C,"), "s.PDF")


def test_the_headers_total_dues_must_match_the_box_total():
    def header(text):
        return [dict(w, text=text) if w["text"] == "1,510.00" and w["top"] < 150 else w for w in OLD_PAGE]

    hdfc.card_summary(header("1,510.50"), "s.PDF")  # ₹1 of rounding is fine (the box total is 1,510.00)
    page = header("1,700.00")
    with pytest.raises(ValueError, match="^s.PDF: total_due doesn't match the summary box") as e:
        hdfc.card_summary(page, "s.PDF")
    assert "1,700" not in str(e.value)


def test_same_line_words_are_not_below_a_label():
    from indian_finance_parsers._words import below, label
    words = _page(("LABEL", 100, 50), ("C9.00", 100, 52), ("C5.00", 100, 70))  # 2 pt of jitter, then the real figure
    assert below(words, label(words, "LABEL"), AMT_) == "C5.00"
    assert below(_page(("LABEL", 100, 50), ("note", 100, 60), ("C5.00", 100, 70)), label(words, "LABEL"), AMT_) is None


def test_a_note_line_is_passed_over_only_when_asked():
    from indian_finance_parsers._words import below, label
    words = _page(("LABEL", 100, 50), ("(Note)", 100, 60), ("C5.00", 100, 70))
    assert below(words, label(words, "LABEL"), AMT_) is None
    assert below(words, label(words, "LABEL"), AMT_, skip=hdfc.NOTE) == "C5.00"


def test_credit_limit_is_not_found_inside_available_credit_limit():
    from indian_finance_parsers._words import label
    words = _page(("Available", 10, 5), ("Credit", 50, 5), ("Limit", 90, 5))
    assert label(words, "Credit", "Limit") is None and label(words, "Available", "Credit", "Limit")


AMT_ = hdfc.AMT
