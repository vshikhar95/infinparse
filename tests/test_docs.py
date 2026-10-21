import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
PKG = ROOT / "src" / "indian_finance_parsers"
SOURCES = ROOT / "docs" / "sources"
HEADINGS = re.findall(r"^## .+$", (SOURCES / "_template.md").read_text(), re.M)
MODULES = sorted(p.stem for kind in ("importers", "purchases", "portfolio")
                 for p in (PKG / kind).glob("*.py") if p.stem != "__init__")


def test_template_has_headings():
    assert len(HEADINGS) == 7


@pytest.mark.parametrize("module", MODULES)
def test_every_module_has_a_runbook_with_every_heading(module):
    doc = SOURCES / f"{module}.md"
    assert doc.exists(), f"missing docs/sources/{module}.md"
    missing = [h for h in HEADINGS if not re.search(rf"^{re.escape(h)}$", doc.read_text(), re.M)]
    assert not missing


@pytest.mark.parametrize("module", MODULES)
def test_readme_links_every_runbook(module):
    assert f"docs/sources/{module}.md" in (ROOT / "README.md").read_text()
