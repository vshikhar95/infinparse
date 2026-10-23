import os
from datetime import date
from decimal import Decimal as D

import pytest
from openpyxl import Workbook

from indian_finance_parsers.portfolio import zerodha_holdings

HDR = ["Symbol", "ISIN", "Sector", "Quantity Available", "Quantity Discrepant", "Quantity Long Term",
       "Quantity Pledged (Margin)", "Quantity Pledged (Loan)", "Average Price", "Previous Closing Price",
       "Unrealized P&L", "Unrealized P&L Pct."]


def _holdings_xlsx(tmp_path):
    p = tmp_path / "holdings-AB1234.xlsx"
    wb = Workbook()
    for r in [["Equity Holdings Statement as on 2026-10-20"], [], ["Client ID", "AB1234"], [], HDR,
              ["FAKECO", "INE000X01011", "IT", 10, 1, 5, 2, 0, 100, 150.5, 0, 0],
              ["TESTBANK", "INE000X01029", "BANKING", 3, 0, 0, 0, 1, 200, 210, 0, 0],
              [None, None, "Total", 16],
              ["Notes: invented"]]:
        wb.active.append([None, *r])  # the real export starts in column B
    wb.save(p)
    return p


def test_holdings(tmp_path):
    rows = zerodha_holdings.parse(_holdings_xlsx(tmp_path))
    assert [(r.name, r.isin, r.units, r.price, r.value) for r in rows] == [
        ("FAKECO", "INE000X01011", D(13), D("150.5"), D("1956.5")),
        ("TESTBANK", "INE000X01029", D(4), D(210), D(840))]
    assert (rows[0].source, rows[0].as_of, rows[0].matures) == ("zerodha", date(2026, 10, 20), None)


def test_account_is_the_client_id_printed_in_the_file(tmp_path):
    assert {r.account for r in zerodha_holdings.parse(_holdings_xlsx(tmp_path))} == {"AB1234"}


def test_account_is_empty_when_the_file_prints_none(tmp_path):
    from openpyxl import load_workbook
    p = _holdings_xlsx(tmp_path)
    wb = load_workbook(p)
    wb.active.delete_rows(3)
    wb.save(p)
    assert {r.account for r in zerodha_holdings.parse(p)} == {""}


def test_as_of_is_the_statement_date_the_file_prints(tmp_path):
    p = _holdings_xlsx(tmp_path)
    os.utime(p, (1_800_000_000, 1_800_000_000))
    assert zerodha_holdings.parse(p)[0].as_of == date(2026, 10, 20)


def test_without_a_printed_date_as_of_falls_back_to_the_argument_then_mtime(tmp_path):
    from openpyxl import load_workbook
    p = _holdings_xlsx(tmp_path)
    wb = load_workbook(p)
    wb.active.delete_rows(1)
    wb.save(p)
    assert zerodha_holdings.parse(p, as_of=date(2026, 1, 2))[0].as_of == date(2026, 1, 2)
    os.utime(p, (1_800_000_000, 1_800_000_000))
    assert zerodha_holdings.parse(p)[0].as_of == date.fromtimestamp(1_800_000_000)


def test_no_header_raises_naming_only_the_file(tmp_path):
    p = tmp_path / "holdings.xlsx"
    wb = Workbook()
    wb.active.append(["nothing here"])
    wb.save(p)
    with pytest.raises(ValueError, match="^holdings.xlsx: no Symbol/ISIN header row"):
        zerodha_holdings.parse(p)


def test_in_memory_file_without_a_printed_date_needs_as_of(tmp_path):
    import io
    from openpyxl import load_workbook
    p = _holdings_xlsx(tmp_path)
    wb = load_workbook(p)
    wb.active.delete_rows(1)
    buf = io.BytesIO()
    wb.save(buf)
    buf.name = "holdings-AB1234.xlsx"
    with pytest.raises(ValueError, match="pass as_of"):
        zerodha_holdings.parse(buf)
    buf.seek(0)
    assert zerodha_holdings.parse(buf, as_of=date(2026, 1, 2))[0].as_of == date(2026, 1, 2)


def test_cost_is_average_price_times_units(tmp_path):
    rows = zerodha_holdings.parse(_holdings_xlsx(tmp_path))
    assert [(r.units, r.cost) for r in rows] == [(D(13), D(1300)), (D(4), D(800))]  # avg 100 x 13, 200 x 4


def test_cost_is_none_without_an_average_price(tmp_path):
    from openpyxl import load_workbook
    p = _holdings_xlsx(tmp_path)
    wb = load_workbook(p)
    for row in wb.active.iter_rows():
        if row[1].value == "Symbol":
            row[9].value = "Avg (renamed)"  # the "Average Price" header cell (column B is index 1)
    wb.save(p)
    assert {r.cost for r in zerodha_holdings.parse(p)} == {None}


def _with_totals(tmp_path, invested, present):
    from openpyxl import load_workbook
    p = _holdings_xlsx(tmp_path)
    wb = load_workbook(p)
    wb.active.insert_rows(4, 2)
    for r, row in ((4, ["Invested Value", invested]), (5, ["Present Value", present])):
        wb.active.cell(r, 2, row[0])
        wb.active.cell(r, 3, row[1])
    wb.save(p)
    return p


def test_sheet_totals_match_the_rows(tmp_path):
    # 13 x 100 + 4 x 200 = 2100 (a cent off is rounding); 13 x 150.5 + 4 x 210 = 2796.5
    assert len(zerodha_holdings.parse(_with_totals(tmp_path, 2100.01, 2796.5))) == 2


@pytest.mark.parametrize("invested,present,field", [(2200, 2796.5, "Invested Value"), (2100, 3000, "Present Value")])
def test_sheet_totals_that_disagree_raise_naming_file_and_field(tmp_path, invested, present, field):
    with pytest.raises(ValueError, match=f"^holdings-AB1234.xlsx: parsed {field} doesn't match") as e:
        zerodha_holdings.parse(_with_totals(tmp_path, invested, present))
    assert "2200" not in str(e.value) and "3000" not in str(e.value)


def test_blank_isin_falls_back_to_a_symbol_that_is_an_isin(tmp_path):
    from openpyxl import load_workbook
    p = _holdings_xlsx(tmp_path)
    wb = load_workbook(p)
    ws = wb.active
    ws.insert_rows(8)
    for c, v in enumerate(["INE000Z00018", None, "UNLISTED", 1, 0, 0, 0, 0, 0, 0, 0, 0], 2):
        ws.cell(8, c, v)
    wb.save(p)
    rows = zerodha_holdings.parse(p)
    assert [(r.name, r.isin) for r in rows] == [("FAKECO", "INE000X01011"), ("TESTBANK", "INE000X01029"),
                                                 ("INE000Z00018", "INE000Z00018")]
    assert zerodha_holdings.parse(_set_isin(p, "FAKECO", None))[0].isin is None  # an ordinary symbol: no fallback


def _set_isin(p, symbol, isin):
    from openpyxl import load_workbook
    wb = load_workbook(p)
    for row in wb.active.iter_rows():
        if row[1].value == symbol:
            row[2].value = isin
    wb.save(p)
    return p
