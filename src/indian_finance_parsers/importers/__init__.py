"""Statement importers: one module per source, each exposing `parse(path) -> list[Txn]` and `meta(path) -> dict`.

Importers know file formats only. Which file maps to which account, and what happens to the rows next,
is the caller's business."""
