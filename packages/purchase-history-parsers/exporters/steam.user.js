// ==UserScript==
// @name         Steam purchase history export (purchase-history-parsers)
// @namespace    infinparse
// @version      0.2.0
// @description  Loads your full history and saves only the history rows for purchase_history_parsers.steam. Runs in your own logged-in session.
// @match        https://store.steampowered.com/account/history*
// @grant        none
// ==/UserScript==
// Use: install in Tampermonkey/Violentmonkey and click the "Export" button on the page, or paste this whole file
// into the browser console on that page while logged in. It reads only the page you are on, and the saved file holds
// only the history rows: no scripts, session data, account email or profile.

function saveFile(name, text) {
  const a = Object.assign(document.createElement("a"), {
    href: URL.createObjectURL(new Blob([text], { type: "text/html" })), download: name,
  });
  a.click();
  URL.revokeObjectURL(a.href);
}

async function loadAll({ more, rows, timeoutMs = 15000 }) {
  // keep loading more history until three rounds in a row add nothing
  for (let idle = 0; idle < 3;) {
    const before = rows();
    const button = more();
    if (button) button.click(); else window.scrollTo(0, document.body.scrollHeight);
    const start = Date.now();
    while (rows() === before && Date.now() - start < timeoutMs / 3) await new Promise((r) => setTimeout(r, 300));
    idle = rows() === before ? idle + 1 : 0;
  }
}

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

const BANNER = "PERSONAL DATA: your purchase history. Keep this file private; never attach it to an issue.";

function buildExport(rowsHtml) {
  // rowsHtml: outerHTML of each tr.wallet_table_row; that table is all the parser reads
  return `<!doctype html>\n<html><head><meta charset="utf-8"><title>Steam purchase history</title></head><body>
<p><strong>${BANNER}</strong></p>
<table class="wallet_history_table">
${rowsHtml.join("\n")}
</table>
</body></html>\n`;
}

async function exportHistory() {
  await loadAll({ more: () => { const b = document.getElementById("load_more_button"); return b?.offsetParent ? b : null; },
                  rows: () => document.querySelectorAll("tr.wallet_table_row").length });
  saveFile('steam-purchase-history.PERSONAL.html', buildExport([...document.querySelectorAll("table.wallet_history_table tr.wallet_table_row")].map((r) => r.outerHTML)));
}

if (typeof module !== "undefined") {
  module.exports = { buildExport };  // tests
} else if (typeof GM_info !== "undefined") {
  const b = Object.assign(document.createElement("button"), { textContent: "Export" });
  b.style.cssText = "position:fixed;bottom:16px;right:16px;z-index:99999;padding:8px 12px";
  b.onclick = async () => { b.disabled = true; b.textContent = "Loading history…"; await exportHistory(); b.textContent = "Saved"; };
  document.body.append(b);
} else {
  exportHistory();
}
