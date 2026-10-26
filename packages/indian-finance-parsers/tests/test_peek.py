from indian_finance_parsers.peek import mask


def test_mask_hides_digits_and_letters():
    out = mask("ACME 1234")
    assert "ACME" not in out and "1234" not in out
    assert out == "XXXX 9999"  # pinned from the original peek.mask: length and separators kept


def test_mask_keeps_header_vocabulary():
    assert mask("Txn Date: Acme") == "Txn Date: Xxxx"


def test_mask_hides_non_ascii_letters():
    assert mask("रमेश 12") == "xxxx 99"


def test_cli_masks_the_file_name(tmp_path):
    import subprocess
    import sys
    p = tmp_path / "1234XXXXXXXX5678_ACME.csv"
    p.write_text("Date,Amount\n01/01/2026,10\n")
    out = subprocess.run([sys.executable, "-m", "indian_finance_parsers.peek", str(p)], capture_output=True, text=True, check=False).stdout
    assert "1234" not in out and "5678" not in out and "ACME" not in out
