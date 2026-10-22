"""Portfolio parsers: holdings snapshots from CAS, broker, PPF, SGB and FD documents.

Most expose `parse(path, **opts) -> list[Holding]`; zerodha exposes holdings(), trades() and ledger() instead."""
