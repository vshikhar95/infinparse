import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "scripts" / "pii_check.sh"
pytestmark = pytest.mark.skipif(not shutil.which("git"), reason="needs git")


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q")
    git(r, "config", "user.email", "1+x@users.noreply.github.com")
    git(r, "config", "user.name", "x")
    return r


def commit(repo, name, text):
    (repo / name).write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "c")


def check(repo, *args):
    return subprocess.run(["bash", str(SCRIPT), *args], cwd=repo, capture_output=True, text=True)


def test_clean_repo_passes(repo):
    commit(repo, "a.py", "x = 1  # card 4111111111111111, acct 0000123456789, order 111111111111, ref 12345678901\n"
                         "@pytest.fixture\n+@decorator in a diff\nsha256:dabe6dad990c06\n")
    assert check(repo).returncode == 0


def test_email_fails_then_history_still_fails(repo):
    commit(repo, "a.py", "owner = 'someone@gmail.com'\n")
    r = check(repo)
    assert r.returncode == 1 and "a.py:1" in r.stdout
    assert "someone" not in r.stdout  # reports where, never the value
    commit(repo, "a.py", "owner = ''\n")
    r = check(repo)
    assert r.returncode == 1 and "a.py:1:" not in r.stdout and "history" in r.stdout  # tree clean, history not


def test_email_never_committed_passes(repo):
    commit(repo, "a.py", "owner = ''\n")
    assert check(repo).returncode == 0


def test_home_path_and_long_digits_fail(repo):
    commit(repo, "a.py", "p = '/Users/x/stmt.pdf'\n")
    assert check(repo).returncode == 1
    commit(repo, "a.py", "acct = '5012345678901'\n")
    assert check(repo).returncode == 1


def test_denylist(repo, tmp_path):
    commit(repo, "a.py", "# paid Zed back\n")
    assert check(repo).returncode == 0
    deny = tmp_path / "deny.txt"
    deny.write_text("\nzed\n")  # blank lines are ignored; matching ignores case
    r = check(repo, str(deny))
    assert r.returncode == 1 and "a.py:1" in r.stdout and "zed" not in r.stdout.lower()


def test_relationship_words_match_whole_words_only(repo):
    commit(repo, "a.py", "# trip to Dadra; motherboard\n")
    assert check(repo).returncode == 0
    commit(repo, "a.py", "# my dad's card\n")
    assert check(repo).returncode == 1


def test_unreadable_denylist_fails_loudly(repo):
    commit(repo, "a.py", "x = 1\n")
    r = check(repo, "no-such-denylist.txt")
    assert r.returncode == 2 and "denylist" in r.stderr


def test_relative_denylist_resolves_from_the_callers_directory(repo, tmp_path):
    commit(repo, "a.py", "# paid Zed back\n")
    (tmp_path / "deny.txt").write_text("zed\n")
    r = subprocess.run(["bash", str(SCRIPT), "../deny.txt"], cwd=repo, capture_output=True, text=True)
    assert r.returncode == 1


def test_filename_with_colon_is_rejected(repo):
    commit(repo, "a:b.py", "x = 1\n")
    r = check(repo)
    assert r.returncode == 1 and "unscannable file name" in r.stdout


def test_binary_files_are_rejected(repo):
    (repo / "orders.zip").write_bytes(b"PK\x03\x04\x00someone@gmail.com\x00")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "c")
    r = check(repo)
    assert r.returncode == 1 and "orders.zip" in r.stdout and "binary" in r.stdout


def test_noreply_exemption_is_per_address(repo):
    commit(repo, "a.py", "# 1+x@users.noreply.github.com\n")
    assert check(repo).returncode == 0
    commit(repo, "a.py", "# 1+x@users.noreply.github.com cc someone@gmail.com\n")
    assert check(repo).returncode == 1


def test_names_with_spaces_are_reported_whole(repo):
    (repo / "my orders.zip").write_bytes(b"PK\x03\x04\x00")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "c")
    r = check(repo)
    assert "my orders.zip: binary file" in r.stdout and "history my orders.zip: binary file" in r.stdout
