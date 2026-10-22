import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SOURCES = ROOT / "docs" / "sources"
HEADINGS = re.findall(r"^## .+$", (SOURCES / "_template.md").read_text(), re.M)
MODULES = sorted(p.stem for p in (ROOT / "src" / "purchase_history_parsers").glob("*.py")
                 if p.stem not in ("__init__", "models"))


@pytest.mark.parametrize("module", MODULES)
def test_every_parser_has_a_runbook_with_every_heading(module):
    doc = SOURCES / f"{module}.md"
    assert doc.exists(), f"missing docs/sources/{module}.md"
    assert not [h for h in HEADINGS if not re.search(rf"^{re.escape(h)}$", doc.read_text(), re.M)]


@pytest.mark.parametrize("module", MODULES)
def test_readme_links_every_runbook(module):
    assert f"docs/sources/{module}.md" in (ROOT / "README.md").read_text()


def test_resolver(tmp_path, monkeypatch):
    from purchase_history_parsers import parser
    assert parser("steam").__name__ == "purchase_history_parsers.steam"
    (tmp_path / "my_stores").mkdir()
    (tmp_path / "my_stores" / "__init__.py").write_text("")
    (tmp_path / "my_stores" / "store.py").write_text("def parse(p): return []")
    monkeypatch.syspath_prepend(tmp_path)
    assert parser("my_stores.store").parse("x") == []
