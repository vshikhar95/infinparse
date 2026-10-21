"""Steam: saved 'Account > View purchase history' page (store.steampowered.com/account/history)."""
import hashlib
import re
from pathlib import Path
from collections import Counter
from datetime import datetime
from decimal import Decimal
from html import unescape

from indian_finance_parsers.models import Purchase

ROW = re.compile(r'(<tr[^>]*class="wallet_table_row[^"]*"[^>]*>)(.*?)</tr>', re.S)


def _cell(row, cls):
    m = re.search(rf'<td[^>]*class="{cls}[^"]*"[^>]*>(.*?)</td>', row, re.S)
    return m.group(1) if m else ""


def _text(html):
    return [unescape(t).strip() for t in re.split(r"<[^>]+>", html) if t.strip()]


def _money(s):
    """'₹ 1,299' -> (Decimal('1299'), 'INR'); '$9.99 USD' -> (Decimal('9.99'), 'USD')."""
    m = re.search(r"[\d,]+(?:\.\d+)?", s)
    if not m:
        return None, ""
    return Decimal(m.group().replace(",", "")), "INR" if "₹" in s else "USD" if "$" in s else s.split()[-1]


def _order_id(transid, row, kind, seen):
    """A purchase and its refund(s) share a transid, so key on transid + kind (+ nth repeat).
    Market rows have no transid: hash the row's text so a re-saved page maps to the same id."""
    if not transid:
        return "h" + hashlib.sha1(" ".join(_text(row)).encode()).hexdigest()[:16]
    key = f"{transid.group(1)}:{kind}"
    seen[key] += 1
    return key if seen[key] == 1 else f"{key}:{seen[key]}"


def parse(path):
    html = Path(path).read_text(encoding="utf-8", errors="replace")
    table = html[html.find('class="wallet_history_table"'):]
    out, seen = [], Counter()
    for tag, row in ROW.findall(table[:table.find("</table>")]):
        transid = re.search(r"transid=(\d+)", tag)
        type_lines = _text(_cell(row, "wht_type"))
        if not type_lines:
            continue  # header-ish rows
        raw_type, payment = type_lines[0], re.sub(r"\s+", " ", " ".join(type_lines[1:]))
        amount, currency = _money(" ".join(_text(_cell(row, "wht_total"))))
        if amount is None:
            continue
        wallet_change = " ".join(_text(_cell(row, "wht_wallet_change")))
        if "Market" in raw_type:
            kind = "market"
        elif "Refund" in raw_type:
            kind, amount = "refund", -amount
        elif "Purchase" in raw_type or "Gift" in raw_type:
            kind = "purchase"
        else:
            kind = "other"
        if kind == "market" and wallet_change.startswith("+"):
            amount = -amount  # sold an item: money came back into the wallet
        charged = None
        if kind == "purchase":
            split = re.match(r"₹ [\d,.]+ Wallet ₹ ([\d,.]+) ", payment)  # "₹ 300 Wallet ₹ 999 Visa"
            charged = _money("₹ " + split.group(1))[0] if split else Decimal(0) if payment.startswith("Wallet") else amount
        orig = re.search(r'wht_original_price">([^<]+)<', row)
        out.append(Purchase(
            store="steam",
            # market rows have no transid: hash the row's text so re-saved pages map to the same id
            order_id=_order_id(transid, row, kind, seen),
            date=datetime.strptime(_text(_cell(row, "wht_date"))[0], "%d %b, %Y").date(),
            items=" | ".join(_text(_cell(row, "wht_items"))),
            kind=kind, amount=amount, currency=currency, payment=payment,
            original_amount=_money(orig.group(1))[0] if orig else None,
            charged=charged, refunded="wht_refunded" in row, raw_type=raw_type,
        ))
    return out
