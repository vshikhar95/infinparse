"""Parse store purchase histories (Steam, Google Play, Humble Bundle, Amazon, PlayStation Store) into plain records.

One module per store export, each exposing `parse(path) -> list[Purchase]`. Parsers read files only; the browser
exporters in `exporters/` produce those files from your own logged-in session."""
from importlib import import_module


def parser(name: str):
    """A bare name ("steam") is a built-in; a dotted path ("mypkg.mystore") is imported as-is."""
    return import_module(name if "." in name else f"purchase_history_parsers.{name}")
