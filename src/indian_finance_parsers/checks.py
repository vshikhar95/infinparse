"""Reconciliation checks over parsed statement rows."""
from itertools import groupby, permutations


def _chains(rows, opening):
    bal = opening
    for r in rows:
        bal += r.amount
        if bal != r.balance_after:
            return False
    return True


def order_by_balance(txns):
    """Banks sometimes print same-day rows out of the order they were applied (a reversal listed before the
    payment it reverses). Re-order each day's rows into the order their running balances prove; a day no
    order can chain is left as printed, for the balance check to reject.
    ponytail: tries every order of a day's rows, so days with more than 7 rows are left as printed."""
    if not txns or any(t.balance_after is None for t in txns):
        return txns
    out, bal = [], None
    for _, day in groupby(txns, key=lambda t: t.date):
        day = list(day)
        start = bal if bal is not None else day[0].balance_after - day[0].amount
        if not _chains(day, start) and len(day) <= 7:
            fixed = next((list(p) for p in permutations(day)
                          if _chains(p, bal if bal is not None else p[0].balance_after - p[0].amount)), None)
            day = fixed or day
        out += day
        bal = day[-1].balance_after
    return out


def check_balance_chain(txns):
    """Bank rows must chain: prev balance + amount == balance_after. Returns opening balance."""
    with_bal = [t for t in txns if t.balance_after is not None]
    if not with_bal:
        return None
    bal = with_bal[0].balance_after - with_bal[0].amount
    opening = bal
    for i, t in enumerate(txns):
        bal += t.amount
        if t.balance_after is not None and bal != t.balance_after:
            raise ValueError(f"balance chain breaks at row {i} ({t.date} {t.description!r}): "
                             f"expected {bal}, statement says {t.balance_after}")
    return opening
