"""ICICI savings account: netbanking 'OpTransactionHistory*.xls' export."""
import re
from datetime import date
from decimal import Decimal

from indian_finance_parsers.checks import check_balance_chain, order_by_balance
from indian_finance_parsers.models import Txn


def _date(s):
    d, m, y = re.fullmatch(r"(\d\d)\D(\d\d)\D(\d{4})", s.strip()).groups()
    return date(int(y), int(m), int(d))


def _amt(s):
    return Decimal(str(s).replace(",", "").strip() or "0")


def parse(path):
    import pandas as pd  # the excel extra; imported here so the PDF importers don't need it
    df = pd.read_excel(path, header=None, dtype=str).fillna("")
    hdr = next(i for i, r in df.iterrows() if any(c.strip() == "S No." for c in r))
    cols = {c.strip(): j for j, c in enumerate(df.iloc[hdr])}
    txns = []
    for _, r in df.iloc[hdr + 1:].iterrows():
        sno, remarks = r.iloc[cols["S No."]].strip(), r.iloc[cols["Transaction Remarks"]].strip()
        if not sno:
            if remarks and txns:  # long remarks wrap onto a row with only the remarks cell
                txns[-1].description += remarks
            continue
        if not sno.isdigit():
            break  # legend/footer starts
        txns.append(Txn(
            date=_date(r.iloc[cols["Transaction Date"]]),
            amount=_amt(r.iloc[cols["Deposit Amount(INR)"]]) - _amt(r.iloc[cols["Withdrawal Amount(INR)"]]),
            description=r.iloc[cols["Transaction Remarks"]].strip(),
            balance_after=_amt(r.iloc[cols["Balance(INR)"]]),
        ))
    expected = sum(1 for v in df.iloc[hdr + 1:, cols["S No."]] if v.strip().isdigit())
    if len(txns) != expected:  # an early stop still passes the balance chain, so count explicitly
        raise ValueError(f"parsed {len(txns)} rows but sheet has {expected} numbered rows")
    if len(txns) > 1 and txns[0].date > txns[-1].date:
        txns.reverse()  # export can be newest-first; the balance chain needs oldest-first
    txns = order_by_balance(txns)
    check_balance_chain(txns)
    return txns


def meta(path):
    return {}
