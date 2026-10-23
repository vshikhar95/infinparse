"""The browser exporters' data-shaping code, run in node, must produce what the parsers read."""
import json
import shutil
import subprocess
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest

from purchase_history_parsers import blinkit, google_play, humble, steam

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


STEAM_ROW = ('<tr class="wallet_table_row " onclick="location.href=\'x?transid=111\'"><td class="wht_date">1 Oct, 2026</td>'
             '<td class="wht_items "><div>Fake Game</div></td><td class="wht_type "><div>Purchase</div>'
             '<div class="wth_payment">Visa **11</div></td><td class="wht_total "> ₹ 1,500 </td>'
             '<td class="wht_wallet_change"></td></tr>')


def test_steam_export_keeps_only_history_rows(tmp_path):
    script = f"""const {{ buildExport }} = require({json.dumps(str(EXPORTERS / "steam.user.js"))});
        process.stdout.write(buildExport([{json.dumps(STEAM_ROW)}]));"""
    out = node(script)
    assert "PERSONAL DATA" in out and "<script" not in out
    (tmp_path / "steam.html").write_text(out)
    [p] = steam.parse(tmp_path / "steam.html")
    assert (p.order_id, p.items, p.amount) == ("111:purchase", "Fake Game", D("1500"))


def test_google_play_export_keeps_only_order_lines(tmp_path):
    page_text = "\n".join(["Account", "someone@example.com", "Order history", "Fake Game Pass", "1 Oct 2026", "₹1,299.00",
                           "Demo App Pro", "Refunded", "19 Sept 2026", "₹99.00", "Help", "Signed in as x@example.com"])
    script = f"""const {{ buildExport }} = require({json.dumps(str(EXPORTERS / "google_play.user.js"))});
        process.stdout.write(buildExport({json.dumps(page_text)}));"""
    out = node(script)
    assert "PERSONAL DATA" in out and "@" not in out and "<script" not in out
    (tmp_path / "play.html").write_text(out)
    rows = google_play.parse(tmp_path / "play.html")
    assert [(p.items, p.amount, p.refunded) for p in rows] == [("Fake Game Pass", D("1299.00"), False),
                                                              ("Demo App Pro", D("99.00"), True)]


# one order from /v1/layout/order_history and its /v1/layout/order_details_v2, trimmed to what the exporter reads (invented)
BLINKIT_LIST = {"data": {"items": [{"tracking": {"common_attributes": {
    "order_id": "ORD1", "order_status": "DELIVERED", "deeplink": "blinkit://order?cart_id=777"}},
    "data": {"subtitle": {"text": "₹150 • 01 Mar 2024"}}}]}}
BLINKIT_DETAIL = {"response": {"snippets": [
    {"widget_type": "image_text_snippet_type_30", "data": {"title": {"text": "Test Milk 500ml"}, "subtitle1": {"text": "500 ml x 2"},
                                                         "subtitle3": {"text": "~~₹60~~ ₹100"}}},
    {"widget_type": "cart_bill_item", "data": {"left_header": {"text": "Bill total"}, "right_header": {"text": "₹150"}}},
    {"widget_type": "text", "data": {"title": {"text": "Paid via Card (XXXX XXXX 4111)"}}},
    {"widget_type": "text", "data": {"title": {"text": "Deliver to"}, "subtitle1": {"text": "1 Fake Street, Nowhere 400001"}}}]}}


def test_blinkit_export_masks_card_and_is_what_the_parser_reads(tmp_path):
    out = node(f"""
        const {{ toRecord }} = require({json.dumps(str(EXPORTERS / "blinkit.user.js"))});
        console.log(JSON.stringify([toRecord({json.dumps(BLINKIT_LIST)}, {json.dumps(BLINKIT_DETAIL)}, "2026-10-23T10:00:00Z")]));""")
    assert "4111" not in out and "Fake Street" not in out and "400001" not in out
    (tmp_path / "blinkit_orders.json").write_text(out)
    [p] = blinkit.parse(tmp_path / "blinkit_orders.json")
    assert (p.order_id, p.date, p.amount, p.payment, p.items) == (
        "ORD1", date(2024, 3, 1), D("150"), "Card", "Test Milk 500ml ×2")


@pytest.mark.parametrize("script,host", [("steam.user.js", "store.steampowered.com"),
                                         ("google_play.user.js", "play.google.com"),
                                         ("humble.user.js", "www.humblebundle.com"),
                                         ("blinkit.user.js", "blinkit.com")])
def test_exporter_header_stays_least_privilege(script, host):
    header = (EXPORTERS / script).read_text().split("// ==/UserScript==")[0]
    grants = [line.split(None, 2)[2].strip() for line in header.splitlines() if line.startswith("// @grant")]
    matches = [line.split(None, 2)[2].strip() for line in header.splitlines() if line.startswith("// @match")]
    assert grants == ["none"]  # no GM_xmlhttpRequest: it could send data to another site
    assert "@connect" not in header and "@require" not in header
    assert matches and all(m.startswith(f"https://{host}/") for m in matches)
