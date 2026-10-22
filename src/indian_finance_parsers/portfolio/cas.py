"""CAMS/KFintech CAS PDF -> mutual fund holdings. Needs the `cas` extra (casparser)."""
from datetime import date
from decimal import Decimal
from pathlib import Path

from indian_finance_parsers.models import Holding


def holdings_from_cas(data: dict) -> list[Holding]:
    """One Holding per scheme (redeemed ones as units 0, value 0, so the folio drops to zero in a later snapshot),
    valued at the statement's valuation date."""
    out = []
    for folio in data["folios"]:
        for s in folio["schemes"]:
            units = Decimal(str(s["close"]))
            v = s["valuation"]
            if units <= 0:
                units, v = Decimal(0), {**v, "value": 0}
            out.append(Holding(date.fromisoformat(str(v["date"])), "cas", folio["folio"], s["scheme"], s["isin"],
                               units, Decimal(str(v["nav"])), Decimal(str(v["value"]))))
    return out


def parse(path, password: str | None = None) -> list[Holding]:
    """casparser opens the encrypted PDF itself, so the password comes here rather than through decrypt.
    A wrong password raises ValueError naming only the file."""
    import casparser
    from casparser.exceptions import IncorrectPasswordError
    try:
        data = casparser.read_cas_pdf(str(path), password).model_dump()
    except IncorrectPasswordError:  # its message carries the full path; from None keeps it out of tracebacks
        raise ValueError(f"{Path(path).name}: wrong or missing password") from None
    return holdings_from_cas(data)
