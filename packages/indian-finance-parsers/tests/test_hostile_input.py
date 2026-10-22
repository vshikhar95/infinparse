"""Crafted files must fail fast or parse fast, never hang on regex backtracking."""
import time

import pytest

from indian_finance_parsers.importers import sbi_ppf
from indian_finance_parsers.portfolio import shriram

N = 60_000


def fast(fn, *args):
    start = time.perf_counter()
    try:
        fn(*args)
    except ValueError:
        pass
    assert time.perf_counter() - start < 2


@pytest.mark.parametrize("body", ["<tr" * N, "<td>" * N + "<" * N])
def test_sbi_ppf(tmp_path, body):
    (tmp_path / "p.html").write_text(body)
    fast(sbi_ppf.parse, tmp_path / "p.html")


def test_shriram():
    fast(shriram.holding_from_text, "1." * N + " % p.a.")
