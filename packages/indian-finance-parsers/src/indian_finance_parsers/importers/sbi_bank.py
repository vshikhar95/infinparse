"""SBI savings account: netbanking 'AccountStatement_*.xlsx' export (password-protected).
Layout: statement date in A4, period in row 17, header row 'Date | Details | Ref No/Cheque No | Debit | Credit | Balance',
oldest first. Netbanking caps one export at 2,000 transactions, so long histories come as several files."""
import re
from datetime import datetime
from decimal import Decimal

from pathlib import Path

from indian_finance_parsers.checks import check_balance_chain, check_totals
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
    opening = check_balance_chain(txns)
    summary = _summary(df)
    if summary:
        _check_summary(summary, txns, opening, Path(getattr(path, "name", path)).name)
    return txns


def _balance(s):
    """'1,900.50CR' -> 1900.50; a 'DR' balance (overdrawn) is negative."""
    return -_amt(s) if str(s).strip().upper().endswith("DR") else _amt(s)


def _summary(df):
    """The "Statement Summary" footer: a header row (Brought Forward, Dr Count, Cr Count, Total Debits, Total Credits,
    Closing Balance) with its figures on the next row. None if the export has no summary."""
    at = next((i for i, r in df.iterrows() if any(c.strip().startswith("Total Debits") for c in r)), None)
    if at is None or at + 1 >= len(df):
        return None
    head = [c.strip() for c in df.iloc[at]]
    vals = dict(zip(head, df.iloc[at + 1], strict=True))  # both rows span the sheet's full width

    def pick(prefix):
        return next((v for k, v in vals.items() if k.startswith(prefix)), None)

    fields = {"opening": pick("Brought Forward"), "dr_count": pick("Dr Count"), "cr_count": pick("Cr Count"),
              "debits": pick("Total Debits"), "credits": pick("Total Credits"), "closing": pick("Closing Balance")}
    if any(v is None or not str(v).strip() for v in fields.values()):
        return None
    return {"opening": _balance(fields["opening"]), "closing": _balance(fields["closing"]),
            "dr_count": int(_amt(fields["dr_count"])), "cr_count": int(_amt(fields["cr_count"])),
            "debits": _amt(fields["debits"]), "credits": _amt(fields["credits"])}


def _check_summary(summary, txns, opening, name):
    """The rows against the statement's own summary: totals, row counts, and the balances at both ends (a dropped
    first or last row still chains, so the ends are checked against the printed figures)."""
    check_totals(txns, name, credits=summary["credits"], debits=summary["debits"])
    if sum(t.amount < 0 for t in txns) != summary["dr_count"]:
        raise ValueError(f"{name}: parsed debit rows don't match the statement's Dr Count")
    if sum(t.amount > 0 for t in txns) != summary["cr_count"]:
        raise ValueError(f"{name}: parsed credit rows don't match the statement's Cr Count")
    if txns and opening != summary["opening"]:
        raise ValueError(f"{name}: the opening balance doesn't match the statement's Brought Forward")
    if txns and txns[-1].balance_after != summary["closing"]:
        raise ValueError(f"{name}: the closing balance doesn't match the statement's Closing Balance")


def meta(path):
    return {}
