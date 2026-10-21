"""Zerodha funds ledger CSV (ledger-<id>-<fy>.csv); parsing lives in portfolio.zerodha."""
from indian_finance_parsers.portfolio.zerodha import ledger as parse


def meta(path):
    return {}
