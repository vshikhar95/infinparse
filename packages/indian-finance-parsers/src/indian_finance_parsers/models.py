"""The records every adapter returns: plain dataclasses, no storage attached."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class Txn:
    date: date
    amount: Decimal  # signed: + money into the account, - money out
    description: str
    balance_after: Decimal | None = None  # bank statements carry it; cards don't
    notes: str = ""  # e.g. which add-on card made a charge


@dataclass
class Holding:
    as_of: date
    source: str          # cas | zerodha | ...
    account: str         # folio / broker client id
    name: str
    isin: str
    units: Decimal
    price: Decimal
    value: Decimal
    matures: date | None = None  # deposits and bonds: the maturity date the document states
    nominee: str = ""    # "; "-joined names as printed; "NA" = document says none; "" = document doesn't say
    cost: Decimal | None = None  # amount invested in the units held, as the document states it; None if it doesn't


@dataclass
class Trade:
    trade_id: str
    date: date
    symbol: str
    isin: str
    side: str            # buy | sell
    quantity: Decimal
    price: Decimal
    exchange: str = "NSE"
