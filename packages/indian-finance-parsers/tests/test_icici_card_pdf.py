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


def _page(*items):
    return [{"text": t, "x0": x, "x1": x + 6 * len(t), "top": top} for t, x, top in items]


# invented figures at the positions the real page 0 prints them: previous 1,000.00 + purchases 5,000.00 +
# cash 100.00 - payments 1,000.00 = total 5,100.00
ICICI_PAGE = _page(
    ("STATEMENT", 79, 187.3), ("DATE", 128, 187.3), ("March", 64, 195.5), ("05,", 120, 195.5), ("2031", 137, 195.5),
    ("PAYMENT", 75, 217.8), ("DUE", 114, 217.8), ("DATE", 133, 217.8), ("March", 70, 225.8), ("25,", 112, 225.8),
    ("2031", 129, 225.8),
    ("Total", 82, 269.0), ("Amount", 103, 269.0), ("due", 132, 269.0), ("`5,100.00", 87, 279.0),
    ("Minimum", 75, 308.8), ("Amount", 109, 308.8), ("due", 139, 308.8), ("`255.00", 91, 318.3),
    ("Previous", 221, 268.5), ("Balance", 250, 268.5), ("Purchases", 305, 268.5), ("Cash", 403, 268.5),
    ("Payments", 488, 268.5),
    ("`1,000.00", 231, 284.5), ("`5,000.00", 318, 284.5), ("`100.00", 418, 284.5), ("`1,000.00", 498, 284.5),
    ("Credit", 208, 327.3), ("Limit", 229, 327.3), ("(Including", 246, 329.2), ("cash)", 269, 329.2),
    ("Available", 290, 327.3), ("Credit", 322, 327.3), ("Cash", 412, 327.3), ("Limit", 430, 327.3),
    ("Available", 495, 327.3), ("Cash", 527, 327.3),
    ("`2,00,000", 208, 340), ("`1,50,000", 291, 340), ("`50,000", 412, 340), ("`40,000", 496, 340))
TEXT = "Statement period : February 06, 2031 to March 05, 2031\n"


def test_card_summary():
    s = icici.card_summary(ICICI_PAGE, "s.pdf", TEXT)
    assert (s.statement_date, s.due_date, s.period_start, s.period_end) == (
        date(2031, 3, 5), date(2031, 3, 25), date(2031, 2, 6), date(2031, 3, 5))
    assert (s.total_due, s.minimum_due, s.previous_balance, s.purchases, s.cash_advances, s.payments, s.charges) == (
        D("5100.00"), D("255.00"), D("1000.00"), D("5000.00"), D("100.00"), D("1000.00"), None)
    assert (s.credit_limit, s.available_credit, s.cash_limit, s.available_cash) == (D(200000), D(150000), D(50000), D(40000))


def test_period_is_optional():
    assert icici.card_summary(ICICI_PAGE, "s.pdf").period_start is None


def _cr(page, x, top):
    """A separate CR word right after a figure."""
    return page + _page(("CR", x, top))


def test_a_cr_figure_is_a_credit_balance():
    # previous 1,000.00 CR: -1000 + 5000 + 100 - 1000 = 3100 owed
    page = [dict(w, text="`3,100.00") if w["text"] == "`5,100.00" else w for w in ICICI_PAGE]
    s = icici.card_summary(_cr(page, 290, 284.5), "s.pdf")
    assert (s.previous_balance, s.total_due) == (D("-1000.00"), D("3100.00"))
    # and the total itself in credit: previous 0 + 0 + 0 - 1,000 payments = 1,000 CR
    page = [dict(w, text="`0.00") if w["text"] in ("`1,000.00", "`5,000.00", "`100.00") and w["x0"] < 420 else w
            for w in ICICI_PAGE]
    page = [dict(w, text="`1,000.00") if w["text"] == "`5,100.00" else w for w in page]
    s = icici.card_summary(_cr(page, 142, 279.0), "s.pdf")
    assert (s.total_due, s.minimum_due) == (D("-1000.00"), D("255.00"))


def test_a_summary_row_that_doesnt_give_the_total_raises_without_amounts():
    page = [dict(w, text="`5,200.00") if w["text"] == "`5,100.00" else w for w in ICICI_PAGE]
    with pytest.raises(ValueError, match="^s.pdf: total_due doesn't follow") as e:
        icici.card_summary(page, "s.pdf")
    assert "5,2" not in str(e.value)


def test_parse_check_summary_still_sees_positive_figures():
    assert icici._figures(ICICI_PAGE) == [D("1000.00"), D("5000.00"), D("100.00"), D("1000.00")]


@pytest.mark.parametrize("old,new,field", [("`255.00", "`9,255.00", "minimum_due"), ("`1,50,000", "`9,50,000", "available_credit"),
                                           ("`40,000", "`90,000", "available_cash")])
def test_inconsistent_figures_raise(old, new, field):
    page = [dict(w, text=new) if w["text"] == old else w for w in ICICI_PAGE]
    with pytest.raises(ValueError, match=f"^s.pdf: {field} is inconsistent"):
        icici.card_summary(page, "s.pdf")


def test_due_date_before_statement_date_raises():
    page = [dict(w, text="01,") if w["text"] == "25," else w for w in ICICI_PAGE]
    with pytest.raises(ValueError, match="^s.pdf: due_date is inconsistent"):
        icici.card_summary(page, "s.pdf")


def test_a_missing_figure_raises_naming_the_field():
    with pytest.raises(ValueError, match="^s.pdf: minimum_due not found"):
        icici.card_summary([w for w in ICICI_PAGE if w["text"] != "`255.00"], "s.pdf")
    with pytest.raises(ValueError, match="^s.pdf: credit limits not found"):
        icici.card_summary([w for w in ICICI_PAGE if w["text"] != "`40,000"], "s.pdf")


def test_doubled_fake_bold_labels_are_read():
    dbl = {"STATEMENT", "DATE", "PAYMENT", "DUE", "Total", "Amount", "due", "Minimum", "Previous"}
    page = [dict(w, text="".join(c * 2 for c in w["text"])) if w["text"] in dbl else w for w in ICICI_PAGE]
    assert icici.card_summary(page, "s.pdf", TEXT) == icici.card_summary(ICICI_PAGE, "s.pdf", TEXT)


def test_only_fully_doubled_words_collapse():
    from indian_finance_parsers._words import norm
    assert [norm(t) for t in ("LOOK", "SSTTAATT", "AA", "ABA")] == ["LOOK", "STAT", "A", "ABA"]


def test_an_overpaid_card_may_have_more_available_than_its_limit():
    # nothing owed, 1,000 CR: available = limit 2,00,000 + 1,000
    page = [dict(w, text="`0.00") if w["text"] in ("`1,000.00", "`5,000.00", "`100.00") and w["x0"] < 420 else w
            for w in ICICI_PAGE]
    page = [dict(w, text="`1,000.00") if w["text"] == "`5,100.00" else w for w in page] + _page(("CR", 142, 279.0))
    page = [dict(w, text="`2,01,000") if w["text"] == "`1,50,000" else w for w in page]
    assert icici.card_summary(page, "s.pdf").available_credit == D(201000)
    page = [dict(w, text="`2,02,000") if w["text"] == "`2,01,000" else w for w in page]
    with pytest.raises(ValueError, match="^s.pdf: available_credit is inconsistent"):
        icici.card_summary(page, "s.pdf")


def test_a_nil_statement_may_print_a_due_date_before_the_statement_date():
    page = [dict(w, text="`0.00") if w["text"] in ("`1,000.00", "`5,000.00", "`100.00", "`5,100.00", "`255.00") else w
            for w in ICICI_PAGE]  # payments figure becomes 0.00 too, so previous 0 + 0 + 0 - 0 = 0
    page = [dict(w, text="01,") if w["text"] == "25," else w for w in page]
    assert icici.card_summary(page, "s.pdf").due_date == date(2031, 3, 1)


def test_a_malformed_date_or_non_month_word_raises_without_the_value():
    with pytest.raises(ValueError) as e:
        icici.card_summary([dict(w, text="45,") if w["text"] == "25," else w for w in ICICI_PAGE], "s.pdf")
    assert str(e.value) == "s.pdf: due_date is unreadable"
    with pytest.raises(ValueError) as e:
        icici.card_summary(ICICI_PAGE, "s.pdf", "Statement period : March 45, 2031 to March 05, 2031")
    assert str(e.value) == "s.pdf: period is unreadable"


def test_a_comma_only_limit_is_not_an_amount():
    with pytest.raises(ValueError, match="^s.pdf: credit limits not found"):
        icici.card_summary([dict(w, text="`,") if w["text"] == "`40,000" else w for w in ICICI_PAGE], "s.pdf")


def test_a_missing_figure_doesnt_borrow_the_next_rows():
    # the statement date's value is not a date; the payment due date's value, 30 pt lower, must not stand in for it
    page = [dict(w, text="Xyzzy") if w["text"] == "March" and w["top"] < 200 else w for w in ICICI_PAGE]
    with pytest.raises(ValueError, match="^s.pdf: statement_date not found"):
        icici.card_summary(page, "s.pdf")


def test_ref_is_the_sernum(rows):
    assert all(len(t.ref) >= 8 and t.ref.isdigit() for t in rows) and rows
    t = icici.rows_from_lines(["03/10/2026 12345678901 TESTMART CITY 10 1,250.50"])[0]
    assert (t.ref, t.description) == ("12345678901", "TESTMART CITY")
