from datetime import date
from decimal import Decimal as D

import pytest
from indian_finance_parsers.models import Trade
from indian_finance_parsers.trades import zerodha_tradebook

TB_HDR = "symbol,isin,trade_date,exchange,segment,series,trade_type,auction,quantity,price,trade_id,order_id,order_execution_time\n"


def _tradebook(tmp_path, name, lines):
    p = tmp_path / name
    p.write_text(TB_HDR + "".join(lines))
    return p


T1 = "FAKECO,INE000X01011,2025-05-02,NSE,EQ,EQ,buy,false,10,100.5,111,900,2025-05-02T10:00:00\n"
T2 = "FAKECO,INE000X01011,2026-01-09,NSE,EQ,EQ,sell,false,4,120,222,901,2026-01-09T10:00:00\n"
T3 = "TESTBANK,INE000X01029,2026-02-03,NSE,EQ,EQ,buy,false,3,200,333,902,2026-02-03T10:00:00\n"


def test_trades_parse(tmp_path):
    t = zerodha_tradebook.parse(_tradebook(tmp_path, "a.csv", [T1]))
    assert t == [Trade("111", date(2025, 5, 2), "FAKECO", "INE000X01011", "buy", D(10), D("100.5"))]


def test_trades_reject_unknown_side(tmp_path):
    with pytest.raises(ValueError, match="trade_type"):
        zerodha_tradebook.parse(_tradebook(tmp_path, "a.csv", [T1.replace(",buy,", ",hold,")]))
