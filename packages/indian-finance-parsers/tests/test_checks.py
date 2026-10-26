from decimal import Decimal as D

import pytest
from indian_finance_parsers.checks import check_balance_chain


@pytest.fixture
def three(txn):
    a = txn("2026-01-01", "-100", "UPI/TESTMART", "900")
    b = txn("2026-01-01", "-100", "UPI/TESTMART", "800")  # identical same-day twin
    c = txn("2026-01-02", "5000", "SALARY", "5800")
    return [a, b, c]


def test_balance_chain_returns_opening_balance(three):
    assert check_balance_chain(three) == D(1000)


def test_broken_balance_chain_raises(txn):
    with pytest.raises(ValueError):
        check_balance_chain([txn("2026-01-01", "-100", "UPI/TESTMART", "900"),
                             txn("2026-01-02", "-50", "X", "999")])


def test_balance_chain_without_balances_is_none(txn):
    assert check_balance_chain([txn("2026-01-01", "-1", "card")]) is None


from indian_finance_parsers.checks import check_totals


def _rows(txn):
    return [txn("2026-01-01", "1000.00", "PAYMENT"), txn("2026-01-02", "-250.00", "SHOP"),
            txn("2026-01-03", "-50.50", "CAFE")]


def test_totals_that_match_pass(txn):
    check_totals(_rows(txn), "s.pdf", credits=D("1000.00"), debits=D("300.50"))
    check_totals(_rows(txn), "s.pdf", debits=[D("280.00"), D("300.50")])  # any printed figure that's acceptable
    check_totals(_rows(txn), "s.pdf")  # nothing printed: nothing to check


def test_missing_credit_names_file_and_field_only(txn):
    with pytest.raises(ValueError, match="^s.pdf: parsed credits don't match the statement's total") as e:
        check_totals(_rows(txn)[1:], "s.pdf", credits=D("1000.00"))
    assert "1000" not in str(e.value)


def test_missing_debit(txn):
    with pytest.raises(ValueError, match="parsed debits don't match"):
        check_totals(_rows(txn)[:2], "s.pdf", debits=D("300.50"))


def test_tolerance_for_documents_that_round(txn):
    check_totals(_rows(txn), "s.pdf", debits=D("301.00"), tolerance=1)
    with pytest.raises(ValueError):
        check_totals(_rows(txn), "s.pdf", debits=D("302.00"), tolerance=1)
