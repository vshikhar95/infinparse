import io

import pikepdf
import pytest

from indian_finance_parsers.decrypt import decrypted


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
    assert str(enc_pdf.parent) not in str(e.value)
    assert e.value.__cause__ is None and e.value.__context__ is None  # no library traceback with the path


def test_wrong_password_office(tmp_path):
    from msoffcrypto.format.ooxml import OOXMLFile
    from openpyxl import Workbook
    plain, enc = io.BytesIO(), tmp_path / "statement.xlsx"
    Workbook().save(plain)
    plain.seek(0)
    with open(enc, "wb") as f:
        OOXMLFile(plain).encrypt("right", f)
    with pytest.raises(ValueError, match="statement.xlsx: wrong or missing password"):
        decrypted(enc, "wrong", tmp_path)
    assert decrypted(enc, "right", tmp_path).read_bytes()[:2] == b"PK"


def test_unsupported_suffix(tmp_path):
    with pytest.raises(ValueError, match="can't decrypt .csv"):
        decrypted(tmp_path / "a.csv", "pw", tmp_path)
