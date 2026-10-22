import tomllib
from pathlib import Path

from indian_finance_parsers import adapter

EXAMPLE = tomllib.loads((Path(__file__).parent.parent / "examples" / "sources.example.toml").read_text())
SECTIONS = {"source": ("importers", "importer"), "purchase_source": ("purchases", "parser"),
            "portfolio_source": ("portfolio", "parser"), "trade_source": ("trades", "parser")}


def test_every_section_is_present():
    assert all(EXAMPLE[section] for section in SECTIONS)


def test_every_named_parser_resolves():
    for section, (kind, key) in SECTIONS.items():
        for s in EXAMPLE[section]:
            assert callable(adapter(kind, s[key]).parse), (section, s[key])
