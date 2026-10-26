from datetime import date
from decimal import Decimal as D

import pytest
from indian_finance_parsers.models import Txn


@pytest.fixture
def txn():
    """Build a Txn: txn("2026-01-01", "-100", "UPI/TESTMART", "900")."""
    def make(day, amount, description, balance_after=None, notes=""):
        return Txn(date.fromisoformat(day), D(amount), description,
                   None if balance_after is None else D(balance_after), notes)
    return make
