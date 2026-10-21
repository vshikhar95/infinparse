"""CAMS/KFintech CAS PDF -> mutual fund holdings. Needs the `cas` extra (casparser)."""
from datetime import date
from decimal import Decimal

from indian_finance_parsers.models import Holding

DEFAULT_OWNERS = {"own": [], "default": "own"}  # no owners given: every scheme is "own"


def owner_of(name: str, owners: dict) -> str:
    low = name.lower()
    return "own" if any(s.lower() in low for s in owners["own"]) else owners["default"]


def holdings_from_cas(data: dict, owners: dict) -> list[Holding]:
    """One Holding per scheme (redeemed ones as units 0, value 0, so the folio drops to zero in net worth), valued at the statement's valuation date."""
    out = []
    for folio in data["folios"]:
        for s in folio["schemes"]:
            units = Decimal(str(s["close"]))
            v = s["valuation"]
            if units <= 0:
                units, v = Decimal(0), {**v, "value": 0}
            out.append(Holding(date.fromisoformat(str(v["date"])), "cas", folio["folio"], s["scheme"], s["isin"],
                               units, Decimal(str(v["nav"])), Decimal(str(v["value"])), owner_of(s["scheme"], owners)))
    return out


def parse(path, owners: dict | None = None, password: str | None = None) -> list[Holding]:
    """owners: {"own": [scheme-name substrings], "default": owner for every other scheme}."""
    import casparser
    data = casparser.read_cas_pdf(str(path), password).model_dump()
    return holdings_from_cas(data, owners or DEFAULT_OWNERS)
