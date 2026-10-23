// ==UserScript==
// @name         Blinkit order export (purchase-history-parsers)
// @namespace    infinparse
// @version      0.1.0
// @description  Downloads blinkit-orders.PERSONAL.json for purchase_history_parsers.blinkit. Runs in your own logged-in session.
// @match        https://blinkit.com/account/orders*
// @grant        none
// ==/UserScript==
// Use: install in Tampermonkey/Violentmonkey and click the "Export orders" button on your Orders page,
// or paste this whole file into the browser console on blinkit.com/account/orders while logged in.
// Blinkit has no public API: this calls the same server-driven-UI endpoints the page itself uses
// (/v1/layout/order_history for the list, /v1/layout/order_details_v2 per order), with the same auth headers
// the page builds from your own localStorage/sessionStorage. Nothing is hard-coded or saved beyond the orders.
// Address, phone and name rows in the detail response are never read.

const DELAY_MS = 1500;  // polite: one call at a time, 429s are real after ~25 quick calls
const MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];

function headers() {
  const loc = JSON.parse(localStorage.location ?? "{}").coords ?? {};
  const h = {
    "Content-Type": "application/json",
    auth_key: localStorage.authKey,
    access_token: JSON.parse(localStorage.auth ?? "{}").accessToken,
    device_id: localStorage.deviceId,
    session_uuid: sessionStorage.sessionId,
    app_client: "consumer_web",
    // the page sends its build versions; these literals are accepted by the API as of 2026-10
    app_version: "52434332",
    web_app_version: String(1_008_010_016),
    rn_bundle_version: String(1_009_003_012),
  };
  if (loc.lat != null) { h.lat = String(loc.lat); h.lon = String(loc.lon); }
  return h;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function post(url, body, log = () => {}) {
  for (let attempt = 0, wait = 10000; ; attempt++) {
    const r = await fetch(url, { method: "POST", credentials: "include", headers: headers(), body: JSON.stringify(body ?? {}) });
    if (r.status === 429 && attempt < 8) { log(`429, backing off ${wait / 1000}s`); await sleep(wait); wait = Math.min(wait * 2, 120000); continue; }
    if (!r.ok) throw new Error(`${url.split("?")[0]} -> HTTP ${r.status}`);
    return r.json();
  }
}

const money = (s) => {  // "₹1,328" / "-₹20" / "+₹5" / "₹ 12.50" -> number, else null
  const m = /(-)?[+-]?\s*₹\s*([\d,]+(?:\.\d+)?)/.exec(String(s ?? ""));
  return m ? (m[1] ? -1 : 1) * Number(m[2].replace(/,/g, "")) : null;
};

// "Card (XXXX XXXX 1234)" -> "Card": no card digits leave the page
const maskPayment = (s) => s.replace(/\([^)]*\)/g, "").replace(/[\d*•]+|\bX{2,}\b/gi, "").replace(/\s+/g, " ").trim();

const iso = (y, m, d) => `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;

// "Today, 12:37 pm" / "Yesterday" / "17 Oct, 9:56 am" / "08 Jun 2025"; yearless dates resolve to the latest date not after exportedAt
function parseDate(text, exportedAt) {
  const t = String(text ?? "");
  const now = new Date(exportedAt);
  if (/today/i.test(t)) return iso(now.getFullYear(), now.getMonth(), now.getDate());
  if (/yesterday/i.test(t)) { const y = new Date(now); y.setDate(y.getDate() - 1); return iso(y.getFullYear(), y.getMonth(), y.getDate()); }
  const m = /\b(\d{1,2})\s+([A-Za-z]{3})[a-z]*(?:,?\s+(\d{4}))?/.exec(t);
  if (!m) return null;
  const mon = MONTHS.indexOf(m[2].toLowerCase());
  const day = Number(m[1]);
  if (mon < 0) return null;
  if (m[3]) return iso(Number(m[3]), mon, day);
  let y = now.getFullYear();
  if (new Date(y, mon, day) > new Date(now.getFullYear(), now.getMonth(), now.getDate())) y -= 1;
  return iso(y, mon, day);
}

const texts = (o, out = []) => {  // every {text: "..."} string under o
  if (Array.isArray(o)) for (const e of o) texts(e, out);
  else if (o && typeof o === "object") for (const [k, v] of Object.entries(o)) typeof v === "string" && k === "text" ? out.push(v) : texts(v, out);
  return out;
};

function listOrder(snippet) {  // one order_history_container_vr from the list response
  const head = snippet.data?.items?.[0];
  const ca = head?.tracking?.common_attributes ?? {};
  return {
    id: ca.order_id ?? null,
    cart_id: /cart_id=(\d+)/.exec(ca.deeplink ?? "")?.[1] ?? null,
    status: ca.order_status ?? null,
    subtitle: head?.data?.subtitle?.text ?? null,  // "₹<total> • <date>"
  };
}

function toRecord(listSnippet, detail, exportedAt) {
  const o = listOrder(listSnippet);
  const snips = detail?.response?.snippets ?? [];
  const items = snips
    .filter((s) => s.widget_type?.includes("image_text_snippet_type_30") && s.data?.subtitle3?.text && s.data?.title?.text)
    .map((s) => ({
      name: s.data.title.text.trim(),
      qty: Number(/x\s*(\d+)\s*$/i.exec(s.data.subtitle1?.text ?? "")?.[1] ?? 1),
      price: money(s.data.subtitle3.text.replace(/~~.*?~~/g, "")),  // ~~strike-through mrp~~ then the paid price
    }));
  const bill = snips.filter((s) => s.widget_type === "cart_bill_item").map((s) => ({ label: s.data?.left_header?.text ?? "", amount: s.data?.right_header?.text }));
  const finalRow = bill.find((b) => /bill total|grand total|to pay|amount paid/i.test(b.label)) ?? bill.at(-1);
  const all = snips.flatMap((s) => texts(s.data));
  const paid = all.map((t) => /^Paid via\s+(.+)/i.exec(t)?.[1]).find(Boolean);
  const payment = paid ? maskPayment(paid) : null;
  const placed = snips.find((s) => /order placed/i.test(s.data?.title?.text ?? ""))?.data?.subtitle2?.text;

  const subTotal = o.subtitle ? money(o.subtitle) : null;
  return {
    id: o.id,
    cart_id: o.cart_id,
    date: parseDate(o.subtitle ?? placed, exportedAt),
    total: subTotal ?? (finalRow ? money(finalRow.amount) : null),
    currency: "INR",
    status: o.status,
    payment,
    items,
  };
}

async function exportOrders(progress = {}, exportedAt = new Date()) {
  const log = (m) => { progress.msg = m; console.log(`[blinkit] ${m}`); };
  Object.assign(progress, { phase: "list", orders: 0, detailed: 0, done: false });
  const snippets = [];
  let page = await post("/v1/layout/order_history", {}, log);
  for (;;) {
    for (const s of page.response?.snippets ?? []) if (s.widget_type === "order_history_container_vr") snippets.push(s);
    progress.orders = snippets.length;
    const next = page.response?.pagination?.next_url;
    if (!next) break;
    log(`list: ${snippets.length} orders`);
    await sleep(DELAY_MS);
    page = await post(next, page.postback_params, log);
  }
  progress.phase = "detail";
  const out = [];
  for (const s of snippets) {
    const o = listOrder(s);
    const url = `/v1/layout/order_details_v2?cart_id=${o.cart_id}&order_id=${o.id}`;
    await sleep(DELAY_MS);
    out.push(toRecord(s, await post(url, {}, log), exportedAt));
    progress.detailed = out.length;
    if (out.length % 10 === 0) log(`detail: ${out.length}/${snippets.length}`);
  }
  progress.phase = "download";
  if (typeof document !== "undefined") download("blinkit-orders.PERSONAL.json", JSON.stringify(out, null, 1));  // personal data: keep it private
  progress.done = true;
  log(`done: ${out.length} orders`);
  return out.length;
}

function download(name, text) {
  const a = Object.assign(document.createElement("a"), {
    href: URL.createObjectURL(new Blob([text], { type: "application/json" })), download: name,
  });
  a.click();
  URL.revokeObjectURL(a.href);
}

if (typeof module !== "undefined") {
  module.exports = { toRecord, parseDate, money, listOrder, maskPayment };  // tests
} else if (typeof GM_info !== "undefined") {
  const b = Object.assign(document.createElement("button"), { textContent: "Export orders" });
  b.style.cssText = "position:fixed;bottom:16px;right:16px;z-index:99999;padding:8px 12px";
  b.onclick = async () => { b.disabled = true; const p = {}; const t = setInterval(() => { b.textContent = `${p.phase}: ${p.detailed ?? 0}/${p.orders ?? 0}`; }, 1000); b.textContent = `Exported ${await exportOrders(p)} orders`; clearInterval(t); };
  document.body.append(b);
} else {
  exportOrders().then((n) => console.log(`blinkit-orders.PERSONAL.json: ${n} orders`));
}
