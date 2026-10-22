"""The browser exporters' data-shaping code, run in node, must produce what the parsers read."""
import json
import shutil
import subprocess
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest

from purchase_history_parsers import humble

EXPORTERS = Path(__file__).parent.parent / "exporters"
pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="needs node")

# one /api/v1/order/<gamekey> response, trimmed to the fields the exporter reads (values invented)
API_ORDER = {"created": "2026-01-05T10:00:00", "amount_spent": 12.49, "total": 12.49, "currency": "USD",
             "product": {"human_name": "Humble Test Bundle", "category": "bundle"},
             "subproducts": [{"human_name": "Game One"}, {"human_name": "Game Two"}],
             "is_giftee": False, "claimed": True, "gamekey_secret_field": "never copied"}


def node(script):
    return subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout


def test_humble_export_is_what_the_parser_reads(tmp_path):
    out = node(f"""
        const {{ orderId, toRecord }} = require({json.dumps(str(EXPORTERS / "humble.user.js"))});
        orderId("SECRETGAMEKEY").then(id => console.log(JSON.stringify([toRecord({json.dumps(API_ORDER)}, id)])));""")
    records = json.loads(out)
    assert "SECRETGAMEKEY" not in out and "never copied" not in out
    assert len(records[0]["id"]) == 16
    (tmp_path / "humble_orders.json").write_text(out)
    [p] = humble.parse(tmp_path / "humble_orders.json")
    assert (p.order_id, p.date, p.amount, p.currency, p.items) == (
        records[0]["id"], date(2026, 1, 5), D("12.49"), "USD", "Humble Test Bundle: Game One | Game Two")


def test_humble_order_ids_are_stable_hashes():
    script = f"""const {{ orderId }} = require({json.dumps(str(EXPORTERS / "humble.user.js"))});
        Promise.all([orderId("K1"), orderId("K1"), orderId("K2")]).then(ids => console.log(JSON.stringify(ids)));"""
    a, b, c = json.loads(node(script))
    assert a == b != c


@pytest.mark.parametrize("script", sorted(p.name for p in EXPORTERS.glob("*.user.js")))
def test_exporter_is_valid_javascript(script):
    subprocess.run(["node", "--check", str(EXPORTERS / script)], check=True)
