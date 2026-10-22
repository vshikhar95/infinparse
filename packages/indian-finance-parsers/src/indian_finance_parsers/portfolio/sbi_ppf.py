"""SBI PPF balance as a holding, from the same saved transaction page as importers.sbi_ppf.
The page prints no account number, so account is "" for the caller to name."""
from decimal import Decimal

from indian_finance_parsers.importers import sbi_ppf
from indian_finance_parsers.models import Holding


def parse(path) -> list[Holding]:
    last = sbi_ppf.parse(path)[-1]
    return [Holding(as_of=last.date, source="ppf", account="", name="SBI PPF", isin="SBI-PPF",
                    units=Decimal(1), price=last.balance_after, value=last.balance_after)]
