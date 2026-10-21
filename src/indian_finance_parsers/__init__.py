"""Parse Indian bank, card, broker and store statements into plain Python records."""
from importlib import import_module


def adapter(kind: str, name: str):
    """kind: "importers" | "purchases" | "portfolio". A bare name is a built-in; a dotted path ("mypkg.mybank")
    is imported as-is, so your own adapters need no registration."""
    return import_module(name if "." in name else f"indian_finance_parsers.{kind}.{name}")


def meta(mod, path) -> dict:
    """The adapter's meta(path) (account-key placeholders such as last4/bin4), or {} if it has none."""
    return getattr(mod, "meta", lambda p: {})(path)
