"""Zerodha Console holdings export (holdings-<client id>.xlsx). Needs the `excel` extra (openpyxl)."""
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

from indian_finance_parsers.models import Holding

QTY = ["Quantity Available", "Quantity Discrepant", "Quantity Pledged (Margin)", "Quantity Pledged (Loan)"]


def _dec(v) -> Decimal:
    return Decimal(str(v or 0).replace(",", "").strip() or 0)


def parse(path, as_of: date | None = None) -> list[Holding]:
    """Rows under the Symbol/ISIN header until the first blank Symbol. From the preamble: account = the Client ID,
    or ""; as_of = the "Statement as on YYYY-MM-DD" date, else the as_of argument, else the file's mtime."""
    from openpyxl import load_workbook
    rows = iter(load_workbook(path, data_only=True).active.iter_rows(values_only=True))
    client, printed = "", None
    for hdr in rows:
        cells = [c for c in hdr or () if c is not None]  # the export starts in column B, so find labels anywhere
        if "Client ID" in cells[:-1]:
            client = str(cells[cells.index("Client ID") + 1])
        if m := next((re.search(r"as on (\d{4}-\d\d-\d\d)", c) for c in cells if isinstance(c, str) and "as on" in c), None):
            printed = date.fromisoformat(m[1])
        if "Symbol" in cells and "ISIN" in cells:
            break
    else:
        raise ValueError(f"{Path(getattr(path, 'name', path)).name}: no Symbol/ISIN header row")
    if not (printed or as_of or isinstance(path, (str, Path))):
        raise ValueError(f"{getattr(path, 'name', 'file')}: no statement date in the file; pass as_of")
    as_of = printed or as_of or date.fromtimestamp(Path(path).stat().st_mtime)
    ix = {h: i for i, h in enumerate(hdr)}
    out = []
    for r in rows:
        if not r[ix["Symbol"]]:
            break
        units = sum(_dec(r[ix[q]]) for q in QTY)
        price = _dec(r[ix["Previous Closing Price"]])
        avg = _dec(r[ix["Average Price"]]) if "Average Price" in ix else Decimal(0)
        out.append(Holding(as_of, "zerodha", client, r[ix["Symbol"]], r[ix["ISIN"]], units, price, units * price,
                           cost=units * avg if avg else None))  # the sheet's average buy price x the units held
    return out
