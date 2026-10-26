"""Canary for pdfplumber drift: build a real PDF with the SBI Card layout (synthetic values, generated at test time, so
no PDF is committed) and parse it end to end. Catches a pdfplumber change in how words and positions are extracted;
it can't catch layout changes in real bank PDFs."""
import json
from pathlib import Path

from fpdf import FPDF
from indian_finance_parsers.importers import sbi_card

WORDS = json.loads((Path(__file__).parent / "fixtures" / "sbi_card_words.json").read_text())


def test_sbi_card_pdf_parses_like_its_extracted_words(tmp_path):
    pdf = FPDF(unit="pt", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", size=9)
    for w in WORDS:
        pdf.text(w["x0"], w["top"] + 7, w["text"].replace("₹", "Rs"))  # baseline sits below the word's top
    path = tmp_path / "Transaction_history.pdf"
    pdf.output(str(path))
    expected = sorted(sbi_card.rows_from_words(WORDS), key=lambda t: t.date)
    assert sbi_card.parse(path) == expected and expected
