"""SBI savings account: netbanking 'AccountStatement_*.xlsx' export (password-protected).
Layout: statement date in A4, period in row 17, header row 'Date | Details | Ref No/Cheque No | Debit | Credit | Balance',
oldest first. Netbanking caps one export at 2,000 transactions, so long histories come as several files."""
import re
from datetime import datetime
from decimal import Decimal

from indian_finance_parsers.models import Txn

DATE_FORMATS = ("%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d-%b-%Y", "%d-%b-%y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d")


def _date(s):
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            pass
    return None


def _amt(s):
    s = re.sub(r"[^\d.\-]", "", str(s))  # drops commas, ₹, Cr/Dr markers
    return Decimal(s) if s not in ("", "-", ".") else Decimal(0)


def parse(path):
    import pandas as pd  # the excel extra; imported here so the PDF importers don't need it
    df = pd.read_excel(path, header=None, dtype=str).fillna("")
    hdr = next(i for i, r in df.iterrows() if {"Date", "Balance"} <= {c.strip() for c in r})
    cols = {c.strip(): j for j, c in enumerate(df.iloc[hdr]) if c.strip()}
    txns = []
    for _, r in df.iloc[hdr + 1:].iterrows():
        d = _date(r.iloc[cols["Date"]])
        if d is None:
            if not r.iloc[cols["Date"]].strip() and r.iloc[cols["Details"]].strip() and txns:
                txns[-1].description += " " + r.iloc[cols["Details"]].strip()  # wrapped details
                continue
            break  # footer / end of table
        txns.append(Txn(
            date=d,
            amount=_amt(r.iloc[cols["Credit"]]) - _amt(r.iloc[cols["Debit"]]),
            description=re.sub(r"\s+", " ", r.iloc[cols["Details"]]).strip(),
            balance_after=_amt(r.iloc[cols["Balance"]]),
        ))
    expected = sum(1 for v in df.iloc[hdr + 1:, cols["Date"]] if _date(v))
    if len(txns) != expected:  # an early stop still passes the balance chain, so count explicitly
        raise ValueError(f"parsed {len(txns)} rows but sheet has {expected} dated rows")
    return txns


def meta(path):
    return {}
