import traceback
from datetime import date
from decimal import Decimal

import casparser
import pytest
from casparser.exceptions import IncorrectPasswordError

from indian_finance_parsers.portfolio import cas

CAS = {
    "statement_period": {"from_": "01-Jan-2020", "to": "20-Oct-2026"},
    "folios": [{"amc": "Acme MF", "folio": "1234567/89", "schemes": [
        {"scheme": "Acme Growth Fund - Direct Growth", "isin": "INF000X01011", "close": 10.5,
         "nominees": ["TEST NOMINEE ONE", "TEST NOMINEE TWO"],
         "valuation": {"date": "2026-10-20", "nav": 100.25, "value": 1052.63}, "transactions": []},
        {"scheme": "Acme Liquid Fund", "isin": "INF000X01029", "close": 2,
         "valuation": {"date": "2026-10-20", "nav": 50, "value": 100}, "transactions": []},
        {"scheme": "Acme Old Fund", "isin": "INF000X01037", "close": 0,
         "valuation": {"date": "2026-10-20", "nav": 10, "value": 0}, "transactions": []},
    ]}],
}


class _Cas:
    def __init__(self, data):
        self.data = data

    def model_dump(self):
        return self.data


@pytest.fixture
def seen(monkeypatch):
    seen = {}
    monkeypatch.setattr(casparser, "read_cas_pdf", lambda path, password: seen.update(pw=password) or _Cas(CAS))
    return seen


def test_one_holding_per_scheme_valued_at_the_statement_date(seen):
    rows = cas.parse("cas.pdf")
    assert [r.name for r in rows] == ["Acme Growth Fund - Direct Growth", "Acme Liquid Fund", "Acme Old Fund"]
    h = rows[0]
    assert (h.as_of, h.source, h.account, h.isin) == (date(2026, 10, 20), "cas", "1234567/89", "INF000X01011")
    assert (h.units, h.price, h.value, h.matures) == (Decimal("10.5"), Decimal("100.25"), Decimal("1052.63"), None)


def test_redeemed_scheme_is_kept_at_zero(seen):
    r = cas.parse("cas.pdf")[2]
    assert (r.units, r.value, r.as_of) == (0, 0, date(2026, 10, 20))


def test_password_is_passed_to_casparser(seen, monkeypatch):
    monkeypatch.delenv("CAS_PASSWORD", raising=False)
    cas.parse("cas.pdf", password="secret-from-caller")
    assert seen["pw"] == "secret-from-caller"


def test_wrong_password_names_only_the_file(monkeypatch):
    def boom(path, password):
        raise IncorrectPasswordError(f"bad password for {path}")
    monkeypatch.setattr(casparser, "read_cas_pdf", boom)
    pdf = "/secret_dir/cas.pdf"  # a variable, so the traceback's source line doesn't contain the path
    with pytest.raises(ValueError, match="cas.pdf: wrong or missing password") as e:
        cas.parse(pdf, password="wrong")
    assert "secret_dir" not in "".join(traceback.format_exception(e.value))


def test_nominees_as_the_statement_prints_them(seen):
    assert [r.nominee for r in cas.parse("cas.pdf")] == ["TEST NOMINEE ONE; TEST NOMINEE TWO", "", ""]


def test_cost_as_the_statement_prints_it(monkeypatch):
    import copy
    data = copy.deepcopy(CAS)
    data["folios"][0]["schemes"][0]["valuation"]["cost"] = 900.50
    monkeypatch.setattr(casparser, "read_cas_pdf", lambda path, password: _Cas(data))
    rows = cas.parse("cas.pdf")
    assert rows[0].cost == Decimal("900.50")
    assert rows[1].cost is None  # this RTA printed no cost value


def test_cost_is_none_when_the_statement_has_none(seen):
    assert {r.cost for r in cas.parse("cas.pdf")} == {None}
