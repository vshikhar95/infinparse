import tomllib
from pathlib import Path

from indian_finance_parsers import adapter

EXAMPLE = tomllib.loads((Path(__file__).parent.parent / "examples" / "sources.example.toml").read_text())
KIND_MODULE = {"cas": "cas", "zerodha_holdings": "zerodha", "zerodha_tradebook": "zerodha", "shriram_fd": "shriram",
               "sgb": "sgb", "sbi_ppf": "sbi_ppf"}


def test_every_section_is_present():
    assert EXAMPLE["source"] and EXAMPLE["purchase_source"] and EXAMPLE["portfolio_source"]
    assert EXAMPLE["portfolio"]["own"] == []


def test_importers_resolve():
    for s in EXAMPLE["source"]:
        assert hasattr(adapter("importers", s["importer"]), "parse")


def test_purchase_parsers_resolve():
    for s in EXAMPLE["purchase_source"]:
        assert hasattr(adapter("purchases", s["parser"]), "parse")


def test_portfolio_kinds_resolve():
    for s in EXAMPLE["portfolio_source"]:
        assert adapter("portfolio", KIND_MODULE[s["kind"]]).__name__.startswith("indian_finance_parsers.portfolio.")
