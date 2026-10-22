"""Fail if a built sdist or wheel contains anything but the package's own files. A stray real statement left in a
package folder would otherwise ship to PyPI, where it can never be fully removed.
Usage: python scripts/check_dist.py dist/*.tar.gz dist/*.whl"""
import re
import sys
import tarfile
import zipfile

ALLOWED = re.compile(
    r"^(?:[^/]+/)?"  # the sdist's top folder
    r"(?:src/(?:indian_finance_parsers|purchase_history_parsers)/.+\.py"  # sdist sources
    r"|(?:indian_finance_parsers|purchase_history_parsers)/.+\.py"  # wheel sources
    r"|[^/]+\.dist-info/(?:METADATA|WHEEL|RECORD|licenses/LICENSE|entry_points\.txt)"
    r"|PKG-INFO|pyproject\.toml|README\.md|LICENSE|\.gitignore)$")


def members(path):
    if path.endswith(".whl"):
        return zipfile.ZipFile(path).namelist()
    return [m.name for m in tarfile.open(path).getmembers() if m.isfile()]


bad = [f"{path}: {name}" for path in sys.argv[1:] for name in members(path) if not ALLOWED.match(name)]
print("\n".join(bad) or f"ok: {len(sys.argv) - 1} archives contain only package files")
sys.exit(1 if bad else 0)
