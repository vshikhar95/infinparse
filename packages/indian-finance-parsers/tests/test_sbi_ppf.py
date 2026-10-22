"""SBI PPF transaction page (table saved as escaped HTML text) -> current PPF balance holding."""
import html
from datetime import date
from decimal import Decimal as D

import pytest

from indian_finance_parsers.checks import check_balance_chain
from indian_finance_parsers.importers import sbi_ppf as ppf_statement
from indian_finance_parsers.portfolio import sbi_ppf


def page(rows):
    tr = "".join(f'<tr><td>{d}</td><td>{desc}</td><td><img alt="status icon" src="x.svg">₹ {amt}</td><td>₹{bal}</td></tr>'
                 for d, desc, amt, bal in rows)
    table = f"<table><tr><th>Date</th><th>Description</th><th>Amount(₹)</th><th>Balance(₹)</th></tr>{tr}</table>"
    return f"<html><body><p>{html.escape(table)}</p></body></html>"


ROWS = [("09/08/2026", "DEPOSIT TFR- FAKE", "1,50,000.00", "11,50,000.00"),   # newest first, as on the page
        ("31/03/2026", "CREDIT INT-", "70,000.00", "10,00,000.00"),
        ("01/04/2025", "DEPOSIT TFR- FAKE", "1,50,000.00", "9,30,000.00")]


def test_latest_balance_becomes_the_ppf_holding(tmp_path):
    p = tmp_path / "sbi-ppf.html"
    p.write_text(page(ROWS))
    [h] = sbi_ppf.parse(p)
    assert (h.source, h.account, h.as_of, h.value, h.matures) == ("ppf", "", date(2026, 8, 9), D("1150000.00"), None)


def test_rows_that_dont_chain_are_rejected(tmp_path):
    bad = [ROWS[0], ("31/03/2026", "CREDIT INT-", "70,000.00", "9,99,999.00"), ROWS[2]]
    p = tmp_path / "sbi-ppf.html"
    p.write_text(page(bad))
    with pytest.raises(ValueError):
        sbi_ppf.parse(p)


def test_statement_rows_are_oldest_first_signed_by_balance_change(tmp_path):
    p = tmp_path / "sbi-ppf.html"
    p.write_text(page(ROWS))
    t = ppf_statement.parse(p)
    assert [(x.date, x.amount) for x in t] == [(date(2025, 4, 1), D("150000.00")), (date(2026, 3, 31), D("70000.00")),
                                              (date(2026, 8, 9), D("150000.00"))]
    assert check_balance_chain(t) == D("780000.00")  # opening = first balance - first amount


def test_march_31_credits_are_noted_as_ppf_interest(tmp_path):
    p = tmp_path / "sbi-ppf.html"
    p.write_text(page(ROWS))
    assert [x.notes for x in ppf_statement.parse(p)] == ["", "PPF interest", ""]
