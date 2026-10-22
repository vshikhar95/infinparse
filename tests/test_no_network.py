"""The parsers never go online: no parser module imports network code. (Exporters run in the browser and are checked
by their own header test.)"""
import ast
from pathlib import Path

import pytest

NETWORK = {"socket", "ssl", "urllib", "http", "requests", "httpx", "aiohttp", "ftplib", "smtplib", "imaplib", "poplib",
           "telnetlib", "xmlrpc", "websocket", "websockets", "urllib3"}
SOURCES = sorted(Path(__file__).parent.parent.glob("packages/*/src/**/*.py"))


@pytest.mark.parametrize("source", SOURCES, ids=lambda p: str(p).split("/src/")[-1])
def test_no_network_imports(source):
    tree = ast.parse(source.read_text())
    imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imported |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert not {m for m in imported if m.split(".")[0] in NETWORK}
