from datetime import date
from decimal import Decimal as D

import pytest

from indian_finance_parsers.importers import zerodha_ledger

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
    t = zerodha_ledger.parse(p)
    assert [(x.date, x.amount, x.description, x.balance_after) for x in t] == [
        (date(2026, 4, 2), D("500.00"), "Funds added", D("1500.00")),
        (date(2026, 4, 3), D("-300.25"), "Buy FAKECO", D("1199.75")),
        (date(2026, 4, 4), D("10.25"), "Refund", D("1210.00"))]
    assert zerodha_ledger.meta(p) == {}


def test_ledger_closing_mismatch_raises_naming_only_the_file(tmp_path):
    (tmp_path / "secret_dir").mkdir()
    p = tmp_path / "secret_dir" / "ledger.csv"
    p.write_text(LEDGER.replace("Closing Balance,,,,,,1210.00", "Closing Balance,,,,,,1211.00"))
    with pytest.raises(ValueError, match="^ledger.csv: Closing Balance") as e:
        zerodha_ledger.parse(p)
    assert "secret_dir" not in str(e.value)


def test_ledger_without_closing_row(tmp_path):
    p = tmp_path / "ledger.csv"
    p.write_text(LEDGER.replace("Closing Balance,,,,,,1210.00\n", ""))
    assert len(zerodha_ledger.parse(p)) == 3


def test_ledger_rows_must_chain_from_the_opening_balance(tmp_path):
    p = tmp_path / "ledger.csv"
    p.write_text(LEDGER.replace("Opening Balance,,,,,,1000.00", "Opening Balance,,,,,,900.00"))
    with pytest.raises(ValueError, match="Opening Balance"):
        zerodha_ledger.parse(p)


def test_ledger_broken_balance_chain_raises(tmp_path):
    p = tmp_path / "ledger.csv"
    p.write_text(LEDGER.replace("Buy FAKECO,2026-04-03,--,Book Voucher,300.25,,1199.75",
                                "Buy FAKECO,2026-04-03,--,Book Voucher,300.25,,1100.00"))
    with pytest.raises(ValueError, match="balance chain"):
        zerodha_ledger.parse(p)
