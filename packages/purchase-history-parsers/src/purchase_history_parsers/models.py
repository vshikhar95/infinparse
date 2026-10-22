"""The record every store parser returns: a plain dataclass, no storage attached."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


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
