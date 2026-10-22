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
class Purchase:
    store: str
    order_id: str        # store's own id; with store, a stable key (re-parsing a file gives the same ids)
    date: date
    items: str           # " | "-joined item names
    kind: str            # purchase | refund | market | other — store-specific detail stays in raw_type
    amount: Decimal      # money spent (+) or returned (-), in `currency`
    currency: str        # INR, USD, ...
    payment: str = ""    # e.g. "Visa **11", "Wallet", "UPI"
    original_amount: Decimal | None = None  # pre-discount price, when the store shows it
    charged: Decimal | None = None  # part that left a real account (card/UPI); 0 if paid from store credit. None = amount
    refunded: bool = False
    raw_type: str = ""


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
