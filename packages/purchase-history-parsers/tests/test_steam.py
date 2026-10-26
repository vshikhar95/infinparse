import pytest
from purchase_history_parsers import steam

ROW = '''<tr class="wallet_table_row " onclick="location.href='x?transid={tid}'"><td class="wht_date">{d}</td>
<td class="wht_items "><div>{item}</div></td><td class="wht_type "><div>{typ}</div><div class="wth_payment">Visa **11</div></td>
<td class="wht_total "> {amt} </td><td class="wht_wallet_change">{wc}</td></tr>'''


def table(*rows):
    return '<table class="wallet_history_table">' + "".join(rows) + "</table>"


@pytest.fixture
def rows(tmp_path):
    page = tmp_path / "a.html"
    page.write_text(table(
        ROW.format(tid="111", d="5 Oct, 2026", item="Fake Game", typ="Refund", amt="₹ 500", wc=""),
        ROW.format(tid="111", d="1 Oct, 2026", item="Fake Game", typ="Purchase", amt="₹ 1,500", wc=""),
        ROW.format(tid="", d="2 Oct, 2026", item="Case", typ="Market Transaction", amt="₹ 10.50", wc="+₹ 10.50"),
    ))
    return steam.parse(page)


def test_steam_ids(rows):
    ids = [r.order_id for r in rows]
    assert ids[:2] == ["111:refund", "111:purchase"] and ids[2].startswith("h")


def test_refund_and_market_sale_are_negative(rows):
    assert [str(r.amount) for r in rows] == ["-500", "1500", "-10.50"]


def test_card_paid_purchase_charges_full_amount(rows):
    assert rows[1].charged == 1500 and rows[0].charged is None


def test_split_payment_charges_only_card_part(tmp_path):
    split = tmp_path / "b.html"
    split.write_text(table(ROW.format(tid="222", d="1 Oct, 2026", item="X", typ="Purchase", amt="₹ 1,299", wc="")
                           .replace("Visa **11", "₹ 300 Wallet ₹ 999 Visa")))
    assert steam.parse(split)[0].charged == 999


def test_hash_id_is_stable_across_reparses(rows, tmp_path):
    page = tmp_path / "a.html"
    assert steam.parse(page)[2].order_id == rows[2].order_id
