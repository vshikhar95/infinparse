"""Synthetic data only: every name, number and address here is made up."""
import importlib.util
import re
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location("anonymise", Path(__file__).parents[1] / "tools/anonymise.py")
anonymise = importlib.util.module_from_spec(_spec)
sys.modules["anonymise"] = anonymise
_spec.loader.exec_module(anonymise)

DOC = """file: stmt_4111XXXXXXXX9876.pdf
Customer Name : PRAKASH TIWARI              Statement Date : 12/03/2026
Address : 14 Lotus Lane, Pune - 411001      Interest Frequency : Quarterly
PAN : ABCPT1234Q   IFSC : HDFC0001234       Account No : 000012345678
Mobile +91 98765 43210   UPI prakash.t@okaxis
Nominee : Sunita Tiwari                    Total Amount Due   1,23,456.78
12/03/2026 | AMAZON PAY INDIA | 2,499.00 Dr | ISIN INE002A01018
Paid by Prakash
12/03/2026,NEFT REF,000012345678,1234.00,Cr
"""


def test_ids_replaced_labels_amounts_dates_kept(monkeypatch, tmp_path):
    deny = tmp_path / "denylist.txt"
    deny.write_text("# comment\nLotus Lane\n")
    monkeypatch.setattr(anonymise, "DENYLIST", deny)
    anonymise.denylist.cache_clear()
    def names(text):
        return [("name", "PRAKASH TIWARI"), ("name", "Sunita Tiwari")]

    monkeypatch.setitem(anonymise.NER, "fake", names)
    out = anonymise.anonymise(DOC, "fake")
    for secret in ["PRAKASH", "Prakash", "Tiwari", "TIWARI", "Lotus Lane", "411001", "ABCPT1234Q", "HDFC0001234",
                   "000012345678", "98765 43210", "prakash.t@okaxis", "9876"]:
        assert secret not in out, secret
    for kept in ["Interest Frequency : Quarterly", "Total Amount Due   1,23,456.78", "12/03/2026 | AMAZON PAY INDIA",
                 "2,499.00 Dr", "INE002A01018", "12/03/2026,NEFT REF,", ",1234.00,Cr", "Customer Name : ", "Nominee : ", "stmt_", "XXXXXXXX"]:
        assert kept in out, kept
    assert [len(line) for line in out.splitlines()] == [len(line) for line in DOC.splitlines()]  # layout kept
    assert re.search(r"PAN : [A-Z]{5}\d{4}[A-Z] ", out)
    assert anonymise.leaks(out) == 0 and anonymise.leaks(DOC) == 1
