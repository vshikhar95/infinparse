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


@dataclass
class CardSummary:
    """A credit card statement's own header figures. Optional extras: `summary(path)` next to `parse(path)`."""
    statement_date: date
    due_date: date
    total_due: Decimal       # negative when the statement prints a credit balance
    minimum_due: Decimal
    previous_balance: Decimal
    payments: Decimal        # payments and credits, positive
    purchases: Decimal
    credit_limit: Decimal
    available_credit: Decimal
    period_start: date | None = None
    period_end: date | None = None
    charges: Decimal | None = None        # finance charges, where the layout prints them (HDFC)
    cash_advances: Decimal | None = None  # where the layout prints them (ICICI)
    cash_limit: Decimal | None = None     # the cash limit itself, where printed
    available_cash: Decimal | None = None



@dataclass
class Deposit:
    """A fixed deposit as its receipt states it. Optional extra: `deposits(path)` next to `parse(path)`."""
    deposit_no: str
    deposited: date
    amount: Decimal
    rate: Decimal | None     # % p.a., where printed
    tenure_months: int | None
    matures: date
    maturity_amount: Decimal
    scheme: str              # as printed, e.g. "Cumulative"
    interest_payout: str     # as printed, e.g. "Payable on Maturity"; "" if not printed
    nominee: str = ""        # same convention as Holding.nominee
    tenure_days: int | None = None  # days beyond the whole months, where the receipt prints them ("12M 5D")
