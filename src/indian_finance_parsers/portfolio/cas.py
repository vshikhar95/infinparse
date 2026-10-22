"""CAMS/KFintech CAS PDF -> mutual fund holdings. Needs the `cas` extra (casparser)."""
from datetime import date
from decimal import Decimal
from pathlib import Path

from indian_finance_parsers.models import Holding

UNCONFIRMED = "unconfirmed"  # owner when the caller didn't say: visible, never silently "own"


def owner_of(name: str, owners: dict) -> str:
    low = name.lower()
    return "own" if any(s.lower() in low for s in owners.get("own", [])) else owners.get("default", UNCONFIRMED)


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
    """owners: {"own": [scheme-name substrings], "default": owner for every other scheme}.
    Without owners every holding is "unconfirmed"; a wrong password raises ValueError naming only the file."""
    import casparser
    from casparser.exceptions import IncorrectPasswordError
    try:
        data = casparser.read_cas_pdf(str(path), password).model_dump()
    except IncorrectPasswordError:  # its message carries the full path; from None keeps it out of tracebacks
        raise ValueError(f"{Path(path).name}: wrong or missing password") from None
    return holdings_from_cas(data, owners or {})
