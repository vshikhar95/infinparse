"""Store purchase-history parsers: one module per store, each exposing `parse(path) -> list[Purchase]`.

These record what was bought, from any store, as far back as the store's own history goes; they are separate
from bank and card statements, which record money movements."""
