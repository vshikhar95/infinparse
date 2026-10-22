// ==UserScript==
// @name         Google Play order history export (purchase-history-parsers)
// @namespace    infinparse
// @version      0.1.0
// @description  Loads your full history, then saves the page for purchase_history_parsers.google_play. Runs in your own logged-in session.
// @match        https://play.google.com/store/account/orderhistory*
// @grant        none
// ==/UserScript==
// Use: install in Tampermonkey/Violentmonkey and click the "Export" button on the page, or paste this whole file
// into the browser console on that page while logged in. It only reads the page you are on and saves it locally.

// Shared by the page exporters: keep loading more history until the page stops growing, then save it as HTML.
async function loadAll({ more, rows, timeoutMs = 15000 }) {
  // more(): the "load more" control if one is visible, else null; rows(): how many history rows are on the page now
  for (let idle = 0; idle < 3;) {
    const before = rows();
    const button = more();
    if (button) button.click(); else window.scrollTo(0, document.body.scrollHeight);
    const start = Date.now();
    while (rows() === before && Date.now() - start < timeoutMs / 3) await new Promise((r) => setTimeout(r, 300));
    idle = rows() === before ? idle + 1 : 0;  // three quiet rounds in a row: everything is loaded
  }
}

function savePage(name) {
  const html = "<!doctype html>\n" + document.documentElement.outerHTML;
  const a = Object.assign(document.createElement("a"), {
    href: URL.createObjectURL(new Blob([html], { type: "text/html" })), download: name,
  });
  a.click();
  URL.revokeObjectURL(a.href);
}

async function exportHistory() {
  await loadAll({ more: () => [...document.querySelectorAll("button, [role=button]")].find((b) => /^(load|show) more$/i.test(b.textContent.trim())) ?? null,
                  rows: () => (document.body.innerText.match(/₹|\$|€|£/g) ?? []).length });
  savePage('Order history - Google Play.html');
}

if (typeof module === "undefined") {
  if (typeof GM_info !== "undefined") {
    const b = Object.assign(document.createElement("button"), { textContent: "Export" });
    b.style.cssText = "position:fixed;bottom:16px;right:16px;z-index:99999;padding:8px 12px";
    b.onclick = async () => { b.disabled = true; b.textContent = "Loading history…"; await exportHistory(); b.textContent = "Saved"; };
    document.body.append(b);
  } else {
    exportHistory();
  }
}
