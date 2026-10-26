"""Crafted files must fail fast or parse fast, never hang (regex backtracking) or exhaust memory."""
import time
import zipfile

import pytest
from purchase_history_parsers import amazon, google_play, playstation, steam

N = 60_000


def fast(fn, *args):
    start = time.perf_counter()
    try:
        fn(*args)
    except (ValueError, KeyError, IndexError):
        pass  # rejecting a crafted file is fine; hanging is not
    assert time.perf_counter() - start < 2


@pytest.mark.parametrize("body", [
    '<table class="wallet_history_table">' + '<tr class="wallet_table_row ' * N,      # unclosed rows
    '<table class="wallet_history_table">' + "<" * N,                                  # unclosed tags
])
def test_steam(tmp_path, body):
    (tmp_path / "s.html").write_text(body)
    fast(steam.parse, tmp_path / "s.html")


@pytest.mark.parametrize("body", ["<body>" + "<script" * N, "<body>Order history" + "<" * N])
def test_google_play(tmp_path, body):
    (tmp_path / "g.html").write_text(body)
    fast(google_play.parse, tmp_path / "g.html")


def test_playstation(tmp_path):
    (tmp_path / "p.html").write_text("<style" * N + "<" * N)
    fast(playstation.parse, tmp_path / "p.html")


def test_amazon_zip_bomb_is_refused(tmp_path):
    p = tmp_path / "Your Orders.zip"
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Your Amazon Orders/Order History.csv", "x" * (amazon.MAX_MEMBER_BYTES + 1))
    with pytest.raises(ValueError, match="too large"):
        amazon.parse(p)
