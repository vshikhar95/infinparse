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
    assert check_balance_chain(three) == D("1000")


def test_broken_balance_chain_raises(txn):
    with pytest.raises(ValueError):
        check_balance_chain([txn("2026-01-01", "-100", "UPI/TESTMART", "900"),
                             txn("2026-01-02", "-50", "X", "999")])


def test_balance_chain_without_balances_is_none(txn):
    assert check_balance_chain([txn("2026-01-01", "-1", "card")]) is None
