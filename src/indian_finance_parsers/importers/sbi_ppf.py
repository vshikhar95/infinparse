"""SBI PPF account as a statement (rows chained by balance), from the same saved page as portfolio.sbi_ppf.
PPF interest is credited on 31 March and worded like a deposit, so 31 Mar credits get the note "PPF interest"
for categorisation rules to match on. Not 1 Apr: deposits are commonly made that day."""
from indian_finance_parsers.models import Txn
from indian_finance_parsers.portfolio import sbi_ppf


def parse(path):
    return [Txn(date=d, amount=a, description=desc, balance_after=b,
                notes="PPF interest" if a > 0 and (d.month, d.day) == (3, 31) else "")
            for d, desc, a, b in sbi_ppf.rows(path)]


def meta(path):
    return {}
