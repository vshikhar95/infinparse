import os
from datetime import date
from decimal import Decimal as D

import pytest
from openpyxl import Workbook

from indian_finance_parsers.checks import check_balance_chain
from indian_finance_parsers.models import Trade
from indian_finance_parsers.portfolio import zerodha

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
        wb.active.append(r)
    wb.save(p)
    return p


def test_holdings(tmp_path):
    p = _holdings_xlsx(tmp_path)
    rows = zerodha.holdings(p, as_of=date(2026, 10, 20))
    assert [(r.name, r.isin, r.units, r.price, r.value) for r in rows] == [
        ("FAKECO", "INE000X01011", D(13), D("150.5"), D("1956.5")),
        ("TESTBANK", "INE000X01029", D(4), D(210), D(840))]
    assert (rows[0].source, rows[0].account, rows[0].owner, rows[0].as_of) == ("zerodha", "Zerodha", "own", date(2026, 10, 20))


def test_holdings_as_of_defaults_to_mtime(tmp_path):
    p = _holdings_xlsx(tmp_path)
    os.utime(p, (1_800_000_000, 1_800_000_000))
    assert zerodha.holdings(p)[0].as_of == date.fromtimestamp(1_800_000_000)


TB_HDR = "symbol,isin,trade_date,exchange,segment,series,trade_type,auction,quantity,price,trade_id,order_id,order_execution_time\n"


def _tradebook(tmp_path, name, lines):
    p = tmp_path / name
    p.write_text(TB_HDR + "".join(lines))
    return p


T1 = "FAKECO,INE000X01011,2025-05-02,NSE,EQ,EQ,buy,false,10,100.5,111,900,2025-05-02T10:00:00\n"
T2 = "FAKECO,INE000X01011,2026-01-09,NSE,EQ,EQ,sell,false,4,120,222,901,2026-01-09T10:00:00\n"
T3 = "TESTBANK,INE000X01029,2026-02-03,NSE,EQ,EQ,buy,false,3,200,333,902,2026-02-03T10:00:00\n"


def test_trades_parse(tmp_path):
    t = zerodha.trades(_tradebook(tmp_path, "a.csv", [T1]))
    assert t == [Trade("111", date(2025, 5, 2), "FAKECO", "INE000X01011", "buy", D(10), D("100.5"))]


LEDGER = """particulars,posting_date,cost_center,voucher_type,debit,credit,net_balance
Opening Balance,,,,,,1000.00
Funds added,2026-04-02,--,Bank Receipts,,500.00,1500.00
Buy FAKECO,2026-04-03,--,Book Voucher,300.25,,1199.75
Refund,2026-04-04,--,Bank Receipts,0,10.25,1210.00
Closing Balance,,,,,,1210.00
"""


def test_ledger(tmp_path):
    p = tmp_path / "ledger.csv"
    p.write_text(LEDGER)
    t = zerodha.ledger(p)
    assert [(x.date, x.amount, x.description, x.balance_after) for x in t] == [
        (date(2026, 4, 2), D("500.00"), "Funds added", D("1500.00")),
        (date(2026, 4, 3), D("-300.25"), "Buy FAKECO", D("1199.75")),
        (date(2026, 4, 4), D("10.25"), "Refund", D("1210.00"))]
    assert zerodha.opening(p) == D("1000.00")
    assert check_balance_chain(t) == D("1000.00")
    assert zerodha.closing(p) == D("1210.00")


def test_ledger_closing_mismatch_raises(tmp_path):
    p = tmp_path / "ledger.csv"
    p.write_text(LEDGER.replace("Closing Balance,,,,,,1210.00", "Closing Balance,,,,,,1211.00"))
    with pytest.raises(ValueError, match="closing"):
        zerodha.ledger(p)


def test_ledger_without_closing_row(tmp_path):
    p = tmp_path / "ledger.csv"
    p.write_text(LEDGER.replace("Closing Balance,,,,,,1210.00\n", ""))
    assert len(zerodha.ledger(p)) == 3 and zerodha.closing(p) is None


def test_trades_reject_unknown_side(tmp_path):
    with pytest.raises(ValueError, match="trade_type"):
        zerodha.trades(_tradebook(tmp_path, "a.csv", [T1.replace(",buy,", ",hold,")]))


def test_ledger_importer_flows_through_statement_chain(tmp_path):
    from indian_finance_parsers.importers import zerodha_ledger
    p = tmp_path / "ledger-AB1234-fy27.csv"
    p.write_text(LEDGER)
    t = zerodha_ledger.parse(p)
    assert zerodha_ledger.meta(p) == {}
    assert check_balance_chain(t) == D("1000.00")


def test_holdings_owner_is_configurable(tmp_path):
    rows = zerodha.holdings(_holdings_xlsx(tmp_path), as_of=date(2026, 10, 20), owner="other")
    assert {r.owner for r in rows} == {"other"}


def test_errors_name_only_the_file(tmp_path):
    (tmp_path / "secret_dir").mkdir()
    p = tmp_path / "secret_dir" / "ledger.csv"
    p.write_text(LEDGER.replace("Closing Balance,,,,,,1210.00", "Closing Balance,,,,,,1211.00"))
    with pytest.raises(ValueError, match="^ledger.csv: closing") as e:
        zerodha.ledger(p)
    assert "secret_dir" not in str(e.value)


def test_ledger_broken_balance_chain_raises(tmp_path):
    p = tmp_path / "ledger.csv"
    p.write_text(LEDGER.replace("Buy FAKECO,2026-04-03,--,Book Voucher,300.25,,1199.75",
                                "Buy FAKECO,2026-04-03,--,Book Voucher,300.25,,1100.00"))
    with pytest.raises(ValueError, match="balance chain"):
        zerodha.ledger(p)
