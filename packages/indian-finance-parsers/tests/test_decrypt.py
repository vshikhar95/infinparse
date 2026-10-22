import io
from pathlib import Path
import traceback

import pikepdf
import pytest

from indian_finance_parsers.decrypt import decrypted


def _printed(exc):
    """What a crash would print: the full traceback, including any chained library error."""
    return "".join(traceback.format_exception(exc))


def _xlsx(path, password=None):
    from msoffcrypto.format.ooxml import OOXMLFile
    from openpyxl import Workbook
    plain = io.BytesIO()
    Workbook().save(plain)
    if password is None:
        path.write_bytes(plain.getvalue())
        return path
    plain.seek(0)
    with open(path, "wb") as f:
        OOXMLFile(plain).encrypt(password, f)
    return path


@pytest.fixture
def enc_pdf(tmp_path):
    p = tmp_path / "in" / "statement.pdf"
    p.parent.mkdir()
    with pikepdf.Pdf.new() as pdf:
        pdf.add_blank_page()
        pdf.save(p, encryption=pikepdf.Encryption(owner="right", user="right"))
    return p


def test_no_password_passthrough(enc_pdf, tmp_path):
    assert decrypted(enc_pdf, None, tmp_path) == enc_pdf


def test_right_password(enc_pdf, tmp_path):
    out = decrypted(enc_pdf, "right", tmp_path)
    assert out.parent == tmp_path
    with pikepdf.open(out) as pdf:
        assert not pdf.is_encrypted


def test_wrong_password(enc_pdf, tmp_path):
    with pytest.raises(ValueError, match="statement.pdf: wrong or missing password") as e:
        decrypted(enc_pdf, "wrong", tmp_path)
    assert str(enc_pdf.parent) not in _printed(e.value)


def test_wrong_password_office(tmp_path):
    (tmp_path / "in").mkdir()
    enc = _xlsx(tmp_path / "in" / "statement.xlsx", "right")
    with pytest.raises(ValueError, match="statement.xlsx: wrong or missing password"):
        decrypted(enc, "wrong", tmp_path)
    assert decrypted(enc, "right", tmp_path).read_bytes()[:2] == b"PK"


def test_unsupported_suffix(tmp_path):
    with pytest.raises(ValueError, match="can't decrypt .csv"):
        decrypted(tmp_path / "a.csv", "pw", tmp_path)


def test_corrupt_pdf_names_only_the_file(tmp_path):
    bad = tmp_path / "secret_dir" / "statement.pdf"
    bad.parent.mkdir()
    bad.write_bytes(b"%PDF-1.7 truncated")
    with pytest.raises(ValueError, match="statement.pdf: not a readable") as e:
        decrypted(bad, "pw", tmp_path)
    assert "secret_dir" not in _printed(e.value)


def test_corrupt_office_file_names_only_the_file(tmp_path):
    bad = tmp_path / "secret_dir" / "statement.xlsx"
    bad.parent.mkdir()
    bad.write_bytes(b"not an office file")
    with pytest.raises(ValueError, match="statement.xlsx: not a readable") as e:
        decrypted(bad, "pw", tmp_path)
    assert "secret_dir" not in _printed(e.value)


def test_unencrypted_files_pass_through_even_with_a_password(tmp_path):
    (tmp_path / "in").mkdir()
    xlsx = _xlsx(tmp_path / "in" / "plain.xlsx")
    pdf = tmp_path / "in" / "plain.pdf"
    with pikepdf.Pdf.new() as p:
        p.add_blank_page()
        p.save(pdf)
    out = tmp_path / "out"
    out.mkdir()
    assert decrypted(xlsx, "pw", out) == xlsx
    assert decrypted(pdf, "pw", out) == pdf


def test_never_overwrites_the_original(enc_pdf):
    with pytest.raises(ValueError, match="statement.pdf: tmpdir is the file's own folder"):
        decrypted(enc_pdf, "right", enc_pdf.parent)
    with pikepdf.open(enc_pdf, password="right") as pdf:
        assert pdf.is_encrypted


def test_decrypted_copy_never_overwrites_an_existing_file(enc_pdf, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / enc_pdf.name).write_text("someone else's file")
    with pytest.raises(ValueError, match="already exists"):
        decrypted(enc_pdf, "right", out)
    assert (out / enc_pdf.name).read_text() == "someone else's file"


def test_no_partial_plaintext_on_failure(tmp_path, monkeypatch):
    import pikepdf
    src = tmp_path / "in" / "statement.pdf"
    src.parent.mkdir()
    with pikepdf.Pdf.new() as pdf:
        pdf.add_blank_page()
        pdf.save(src, encryption=pikepdf.Encryption(owner="right", user="right"))
    out = tmp_path / "out"
    out.mkdir()

    def broken_save(self, target, *a, **k):
        if hasattr(target, "write"):
            target.write(b"%PDF partial plaintext")
        else:
            Path(target).write_bytes(b"%PDF partial plaintext")
        raise pikepdf.PdfError("disk full")
    monkeypatch.setattr(pikepdf.Pdf, "save", broken_save)
    with pytest.raises(ValueError):
        decrypted(src, "right", out)
    assert list(out.iterdir()) == []
