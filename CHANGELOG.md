# Changelog

## 0.1.0 (unreleased)

First release.

- Statement importers: ICICI Bank savings (XLS), ICICI credit card (CSV and PDF), HDFC credit card (PDF),
  SBI savings (XLSX), SBI Card (PDF), SBI PPF (saved page), Zerodha funds ledger (CSV).
- Purchase parsers: Steam, Google Play, Humble Bundle, Amazon, PlayStation Store.
- Portfolio parsers: CAMS/KFintech CAS, Zerodha holdings, SBI PPF, Sovereign Gold Bond certificates, Shriram Finance
  FD receipts.
- Trade parsers: Zerodha tradebook.
- `adapter(kind, name)` resolver (built-in names or dotted paths), `decrypt.decrypted()` for password-protected PDF and
  Excel files, reconciliation checks, and `peek`, a structure viewer that masks personal data.
