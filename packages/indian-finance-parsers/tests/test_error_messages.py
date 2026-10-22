"""Errors must say where (file, row, field), never what: a parser's exception can end up in logs, Sentry or a pasted
bug report, so it must not carry merchant names or amounts."""
import html
import json
from pathlib import Path

import pytest

from indian_finance_parsers.checks import check_balance_chain
from indian_finance_parsers.importers import sbi_card, sbi_ppf, zerodha_ledger

SECRET_NAME, SECRET_AMOUNT = "POISONMERCHANT", "987654.32"


def test_balance_chain(txn):
    with pytest.raises(ValueError, match="row 1") as e:
        check_balance_chain([txn("2026-01-01", "-1", "A", "9"), txn("2026-01-02", f"-{SECRET_AMOUNT}", SECRET_NAME, "1")])
    assert SECRET_NAME not in str(e.value) and SECRET_AMOUNT not in str(e.value)


def test_zerodha_ledger(tmp_path):
    p = tmp_path / "ledger.csv"
    p.write_text("particulars,posting_date,cost_center,voucher_type,debit,credit,net_balance\n"
                 "Opening Balance,,,,,,1000.00\n"
                 f"{SECRET_NAME},2026-04-02,--,x,,{SECRET_AMOUNT},{SECRET_AMOUNT}\n")
    with pytest.raises(ValueError) as e:
        zerodha_ledger.parse(p)
    assert SECRET_NAME not in str(e.value) and SECRET_AMOUNT not in str(e.value) and "1000" not in str(e.value)


def test_sbi_ppf(tmp_path):
    rows = [("09/08/2026", SECRET_NAME, SECRET_AMOUNT, "1.00"), ("01/04/2025", "x", "5.00", "5.00")]
    tr = "".join(f"<tr><td>{d}</td><td>{s}</td><td>{a}</td><td>{b}</td></tr>" for d, s, a, b in rows)
    (tmp_path / "p.html").write_text(f"<p>{html.escape('<table>' + tr + '</table>')}</p>")
    with pytest.raises(ValueError, match="row 2") as e:
        sbi_ppf.parse(tmp_path / "p.html")
    assert SECRET_AMOUNT not in str(e.value) and "2026" not in str(e.value)


def test_sbi_card():
    words = json.loads((Path(__file__).parent / "fixtures" / "sbi_card_words.json").read_text())
    words = [dict(w, text="Refund") if w["text"] == "Debit" else w for w in words]
    with pytest.raises(ValueError, match="unexpected type") as e:
        sbi_card.rows_from_words(words)
    assert "/2026" not in str(e.value)
