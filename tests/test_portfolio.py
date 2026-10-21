from datetime import date
from decimal import Decimal

from indian_finance_parsers.portfolio import cas

OWNERS = {"own": ["acme growth"], "default": "other"}

CAS = {
    "statement_period": {"from_": "01-Jan-2020", "to": "20-Oct-2026"},
    "folios": [{"amc": "Acme MF", "folio": "1234567/89", "schemes": [
        {"scheme": "Acme Growth Fund - Direct Growth", "isin": "INF000X01011", "close": 10.5,
         "valuation": {"date": "2026-10-20", "nav": 100.25, "value": 1052.63}, "transactions": []},
        {"scheme": "Acme Liquid Fund", "isin": "INF000X01029", "close": 2,
         "valuation": {"date": "2026-10-20", "nav": 50, "value": 100}, "transactions": []},
        {"scheme": "Acme Old Fund", "isin": "INF000X01037", "close": 0,
         "valuation": {"date": "2026-10-20", "nav": 10, "value": 0}, "transactions": []},
    ]}],
}


def test_owner_of():
    assert cas.owner_of("ACME GROWTH FUND", OWNERS) == "own"
    assert cas.owner_of("Acme Liquid Fund", OWNERS) == "other"


def test_holdings_from_cas():
    rows = cas.holdings_from_cas(CAS, OWNERS)
    assert [r.name for r in rows] == ["Acme Growth Fund - Direct Growth", "Acme Liquid Fund", "Acme Old Fund"]
    h = rows[0]
    assert (h.as_of, h.source, h.account, h.isin) == (date(2026, 10, 20), "cas", "1234567/89", "INF000X01011")
    assert (h.units, h.price, h.value, h.owner) == (Decimal("10.5"), Decimal("100.25"), Decimal("1052.63"), "own")
    assert rows[1].owner == "other"
    assert (rows[2].units, rows[2].value, rows[2].as_of) == (0, 0, date(2026, 10, 20))  # redeemed: kept as zero


class _Cas:
    def __init__(self, data):
        self.data = data

    def model_dump(self):
        return self.data


def test_cas_owners_argument(monkeypatch):
    import casparser
    monkeypatch.setattr(casparser, "read_cas_pdf", lambda path, password: _Cas(CAS))
    rows = cas.parse("cas.pdf", owners={"own": ["liquid"], "default": "other"}, password="x")
    assert [r.owner for r in rows] == ["other", "own", "other"]


def test_cas_owners_default_to_own():
    assert cas.owner_of("Acme Liquid Fund", cas.DEFAULT_OWNERS) == "own"


def test_cas_password_argument(monkeypatch):
    import casparser
    seen = {}
    monkeypatch.setattr(casparser, "read_cas_pdf", lambda path, password: seen.update(pw=password) or _Cas(CAS))
    monkeypatch.delenv("CAS_PASSWORD", raising=False)
    cas.parse("cas.pdf", password="secret-from-caller")
    assert seen["pw"] == "secret-from-caller"
