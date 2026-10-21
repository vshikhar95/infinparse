from indian_finance_parsers.peek import mask


def test_mask_hides_digits_and_letters():
    out = mask("ACME 1234")
    assert "ACME" not in out and "1234" not in out
    assert out == "XXXX 9999"  # pinned from the original peek.mask: length and separators kept


def test_mask_keeps_header_vocabulary():
    assert mask("Txn Date: Acme") == "Txn Date: Xxxx"
