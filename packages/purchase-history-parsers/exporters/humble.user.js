// ==UserScript==
// @name         Humble Bundle order export (purchase-history-parsers)
// @namespace    infinparse
// @version      0.1.0
// @description  Downloads humble_orders.json for purchase_history_parsers.humble. Runs in your own logged-in session.
// @match        https://www.humblebundle.com/home/purchases*
// @grant        none
// ==/UserScript==
// Use: install in Tampermonkey/Violentmonkey and click the "Export orders" button on your Purchases page,
// or paste this whole file into the browser console on humblebundle.com while logged in.
// Gamekeys (which unlock your games) are never saved: each order id is a hash of its gamekey.

async function orderId(gamekey) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(gamekey));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 16);
}

function toRecord(order, id) {
  // the shape purchase_history_parsers.humble reads; order is one /api/v1/order/<gamekey> response
  return {
    id,
    created: order.created,
    amount_spent: order.amount_spent,
    total: order.total,
    currency: order.currency ?? null,
    product: order.product?.human_name ?? "",
    category: order.product?.category ?? "",
    items: (order.subproducts ?? []).map((s) => s.human_name),
    is_giftee: Boolean(order.is_giftee),
    claimed: Boolean(order.claimed),
  };
}

function download(name, text) {
  const a = Object.assign(document.createElement("a"), {
    href: URL.createObjectURL(new Blob([text], { type: "application/json" })), download: name,
  });
  a.click();
  URL.revokeObjectURL(a.href);
}

async function exportOrders() {
  const keys = await (await fetch("/api/v1/user/order", { credentials: "same-origin" })).json();
  const out = [];
  for (const { gamekey } of keys) {  // one at a time: polite to the site, and a few hundred orders is still quick
    const order = await (await fetch(`/api/v1/order/${gamekey}`, { credentials: "same-origin" })).json();
    out.push(toRecord(order, await orderId(gamekey)));
  }
  download("humble_orders.json", JSON.stringify(out, null, 1));
  return out.length;
}

if (typeof module !== "undefined") {
  module.exports = { orderId, toRecord };  // tests
} else if (typeof GM_info !== "undefined") {
  const b = Object.assign(document.createElement("button"), { textContent: "Export orders" });
  b.style.cssText = "position:fixed;bottom:16px;right:16px;z-index:99999;padding:8px 12px";
  b.onclick = async () => { b.disabled = true; b.textContent = `Exported ${await exportOrders()} orders`; };
  document.body.append(b);
} else {
  exportOrders().then((n) => console.log(`humble_orders.json: ${n} orders`));
}
