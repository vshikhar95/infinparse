"""Same-day rows printed out of the order the bank applied them are re-ordered by their running balances."""
from datetime import date
from decimal import Decimal as D

import pytest

from indian_finance_parsers.checks import order_by_balance
from indian_finance_parsers.models import Txn

DAY = date(2026, 2, 11)


def t(amount, balance, desc="X", day=DAY):
    return Txn(day, D(amount), desc, D(balance))


def test_reversal_printed_before_its_payment_is_put_after_it():
    rows = [t("-100", "900", "OPENING-DAY", date(2026, 2, 10)),
            t("500", "900", "RVSL broker"),   # printed first, but applied second
            t("-500", "400", "broker")]
    assert [r.description for r in order_by_balance(rows)] == ["OPENING-DAY", "broker", "RVSL broker"]


def test_rows_already_in_chain_order_are_untouched():
    rows = [t("-100", "900"), t("-50", "850"), t("25", "875")]
    assert order_by_balance(rows) == rows


def test_rows_that_no_order_can_chain_are_left_for_the_balance_check_to_reject():
    rows = [t("-100", "900"), t("-50", "123")]
    assert order_by_balance(rows) == rows
