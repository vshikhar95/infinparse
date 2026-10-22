import sys

import pytest

from indian_finance_parsers import adapter, meta


def _pkg(tmp_path, monkeypatch, **modules):
    for name in [m for m in sys.modules if m == "mine" or m.startswith("mine.")]:
        monkeypatch.delitem(sys.modules, name)  # each test builds its own `mine` package
    (tmp_path / "mine").mkdir()
    (tmp_path / "mine" / "__init__.py").write_text("")
    for name, src in modules.items():
        (tmp_path / "mine" / f"{name}.py").write_text(src)
    monkeypatch.syspath_prepend(tmp_path)


def test_builtin_name():
    assert adapter("importers", "hdfc_card").__name__ == "indian_finance_parsers.importers.hdfc_card"


def test_builtin_meta():
    mod = adapter("importers", "hdfc_card")
    assert meta(mod, "NNNNXXXXXXXXXXNN_01-04-2026.PDF") == {"bin4": ""}


def test_dotted_path(tmp_path, monkeypatch):
    _pkg(tmp_path, monkeypatch, bank="def parse(p): return []")
    mod = adapter("importers", "mine.bank")
    assert mod.parse("x") == [] and meta(mod, "x") == {}


def test_missing_parse_is_clear(tmp_path, monkeypatch):
    _pkg(tmp_path, monkeypatch, empty="")
    with pytest.raises(AttributeError, match="parse"):
        adapter("importers", "mine.empty").parse  # noqa: B018 (the attribute access is what raises)


def test_unknown_builtin_raises():
    with pytest.raises(ModuleNotFoundError):
        adapter("importers", "no_such_bank")
