"""decrypted(): password-protected PDF/Excel -> the decrypted file in memory (plaintext never touches disk)."""
import io
import traceback
from decimal import Decimal as D

import pdfplumber
import pikepdf
import pytest

from indian_finance_parsers.decrypt import decrypted


def _printed(exc):
    """What a crash would print: the full traceback, including any chained library error."""
    return "".join(traceback.format_exception(exc))


def _xlsx_bytes(rows=()):
    from openpyxl import Workbook
    wb, buf = Workbook(), io.BytesIO()
    for r in rows:
        wb.active.append(r)
    wb.save(buf)
    return buf.getvalue()


def _encrypt_xlsx(path, plain, password):
    from msoffcrypto.format.ooxml import OOXMLFile
    with open(path, "wb") as f:
        OOXMLFile(io.BytesIO(plain)).encrypt(password, f)
    return path


@pytest.fixture
def enc_pdf(tmp_path):
    p = tmp_path / "secret_dir" / "statement.pdf"
    p.parent.mkdir()
    with pikepdf.Pdf.new() as pdf:
        pdf.add_blank_page()
        pdf.save(p, encryption=pikepdf.Encryption(owner="right", user="right"))
    return p


def test_no_password_returns_the_path(enc_pdf):
    assert decrypted(enc_pdf, None) == enc_pdf


def test_right_password_gives_a_named_in_memory_file(enc_pdf, tmp_path):
    before = set(tmp_path.rglob("*"))
    src = decrypted(enc_pdf, "right")
    assert isinstance(src, io.BytesIO) and src.name == "statement.pdf"
    with pdfplumber.open(src) as pdf:
        assert len(pdf.pages) == 1
    assert set(tmp_path.rglob("*")) == before  # nothing written anywhere


def test_wrong_password(enc_pdf):
    with pytest.raises(ValueError, match="^statement.pdf: wrong or missing password") as e:
        decrypted(enc_pdf, "wrong")
    assert "secret_dir" not in _printed(e.value)


def test_corrupt_pdf_names_only_the_file(tmp_path):
    bad = tmp_path / "secret_dir" / "statement.pdf"
    bad.parent.mkdir()
    bad.write_bytes(b"%PDF-1.7 truncated")
    with pytest.raises(ValueError, match="statement.pdf: not a readable") as e:
        decrypted(bad, "pw")
    assert "secret_dir" not in _printed(e.value)


def test_corrupt_office_file_names_only_the_file(tmp_path):
    bad = tmp_path / "secret_dir" / "statement.xlsx"
    bad.parent.mkdir()
    bad.write_bytes(b"not an office file")
    with pytest.raises(ValueError, match="statement.xlsx: not a readable") as e:
        decrypted(bad, "pw")
    assert "secret_dir" not in _printed(e.value)


def test_wrong_password_office(tmp_path):
    enc = _encrypt_xlsx(tmp_path / "statement.xlsx", _xlsx_bytes(), "right")
    with pytest.raises(ValueError, match="statement.xlsx: wrong or missing password"):
        decrypted(enc, "wrong")


def test_unencrypted_files_pass_through_even_with_a_password(tmp_path):
    xlsx = tmp_path / "plain.xlsx"
    xlsx.write_bytes(_xlsx_bytes())
    pdf = tmp_path / "plain.pdf"
    with pikepdf.Pdf.new() as p:
        p.add_blank_page()
        p.save(pdf)
    assert decrypted(xlsx, "pw") == xlsx and decrypted(pdf, "pw") == pdf


def test_unsupported_suffix(tmp_path):
    with pytest.raises(ValueError, match="can't decrypt .csv"):
        decrypted(tmp_path / "a.csv", "pw")


def test_encrypted_bank_statement_parses_from_memory(tmp_path):
    from indian_finance_parsers.importers import sbi_bank
    rows = [["Account Statement"], [], ["Date", "Details", "Ref No/Cheque No", "Debit", "Credit", "Balance"],
            ["01/10/2026", "UPI/TESTMART", "", "100.00", "", "900.00"],
            ["02/10/2026", "SALARY FAKECO", "", "", "1,000.50", "1,900.50"]]
    enc = _encrypt_xlsx(tmp_path / "AccountStatement_1.xlsx", _xlsx_bytes(rows), "right")
    txns = sbi_bank.parse(decrypted(enc, "right"))
    assert [(t.amount, t.description) for t in txns] == [(D("-100.00"), "UPI/TESTMART"), (D("1000.50"), "SALARY FAKECO")]


def test_meta_reads_the_name_of_an_in_memory_file():
    from indian_finance_parsers.importers import hdfc_card, icici_card_pdf
    hdfc = io.BytesIO(b"")
    hdfc.name = "4111XXXXXXXXXX11_01-04-2026.PDF"
    icici = io.BytesIO(b"")
    icici.name = "4111_1_Retail_Platinum_NORM.pdf"
    assert hdfc_card.meta(hdfc) == {"bin4": "4111"} and icici_card_pdf.meta(icici) == {"product": "Platinum"}
