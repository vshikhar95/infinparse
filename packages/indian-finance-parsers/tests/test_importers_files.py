"""Characterisation tests for the file-based importers, using invented fixtures."""
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest
from indian_finance_parsers.importers import icici_bank, icici_card, sbi_bank
from openpyxl import Workbook

FIX = Path(__file__).parent / "fixtures"


def _xlsx(tmp_path, rows):
    p = tmp_path / "s.xlsx"
    wb = Workbook()
    for r in rows:
        wb.active.append(r)
    wb.save(p)
    return p


# --- ICICI card ---

def test_icici_card_variant_a_signs_and_notes():
    t = icici_card.parse(FIX / "icici_card_a.csv")
    assert [(x.date, x.amount, x.description, x.notes) for x in t] == [
        (date(2026, 10, 1), D("5000.00"), "PAYMENT RECEIVED THANK YOU", "card 4111 XXXX XXXX 1111"),
        (date(2026, 10, 3), D("-1250.50"), "TESTMART TESTCITY", "card 4111 XXXX XXXX 1111"),
        (date(2026, 10, 5), D("-300.00"), "DEMO CAFE DEMOTOWN", "card 4111 XXXX XXXX 2222"),
    ]


def test_icici_card_variant_b_signed_amounts():
    t = icici_card.parse(FIX / "icici_card_b.csv")
    assert [(x.date, x.amount, x.notes) for x in t] == [
        (date(2026, 10, 2), D("2000.00"), "card 4111 XXXX XXXX 1111"),
        (date(2026, 10, 4), D("-799.00"), "card 4111 XXXX XXXX 1111"),
        (date(2026, 10, 6), D("-150.25"), "card 4111 XXXX XXXX 2222"),
    ]


@pytest.mark.parametrize("name,acct4", [("icici_card_a.csv", "1234"), ("icici_card_b.csv", "5678")])
def test_icici_card_meta_acct4(name, acct4):
    assert icici_card.meta(FIX / name) == {"acct4": acct4}


def test_icici_card_wrong_field_count_raises(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("Accountno:,1\n03/10/2026,1,SHOP,0,0,10.00\n")
    with pytest.raises(ValueError, match="expected 7"):
        icici_card.parse(p)


# --- ICICI bank ---

ICICI_HDR = [["Account Statement"], [], ["S No.", "Value Date", "Transaction Date", "Cheque Number",
             "Transaction Remarks", "Withdrawal Amount(INR)", "Deposit Amount(INR)", "Balance(INR)"]]


def _icici_sheet(tmp_path, body):
    return _xlsx(tmp_path, ICICI_HDR + body + [["Legends Used in Account Statement"], ["ABC", "Some legend"]])


def test_icici_bank_rows_amounts_and_wrapped_remarks(tmp_path):
    p = _icici_sheet(tmp_path, [
        [1, "01/10/2026", "01/10/2026", "", "UPI/TESTMART/", "100.00", "0.00", "900.00"],
        [None, None, None, None, "ORDER42", None, None, None],
        [2, "02/10/2026", "02/10/2026", "", "SALARY FAKECO", "0.00", "1,000.50", "1,900.50"],
    ])
    t = icici_bank.parse(p)
    assert [(x.date, x.amount, x.description, x.balance_after) for x in t] == [
        (date(2026, 10, 1), D("-100.00"), "UPI/TESTMART/ORDER42", D("900.00")),
        (date(2026, 10, 2), D("1000.50"), "SALARY FAKECO", D("1900.50")),
    ]


def test_icici_bank_newest_first_is_reversed(tmp_path):
    p = _icici_sheet(tmp_path, [
        [1, "", "02/10/2026", "", "B", "0", "50", "150"],
        [2, "", "01/10/2026", "", "A", "0", "100", "100"],
    ])
    assert [x.description for x in icici_bank.parse(p)] == ["A", "B"]


def test_icici_bank_reversal_printed_before_its_payment_is_reordered(tmp_path):
    p = _icici_sheet(tmp_path, [
        [1, "", "10/02/2026", "", "SALARY FAKECO", "0", "1000", "1000"],
        [2, "", "11/02/2026", "", "UPI/RVSLBROKER", "0", "500", "1000"],
        [3, "", "11/02/2026", "", "UPI/BROKER", "500", "0", "500"],
    ])
    assert [x.description for x in icici_bank.parse(p)] == ["SALARY FAKECO", "UPI/BROKER", "UPI/RVSLBROKER"]


def test_icici_bank_dropped_numbered_row_raises(tmp_path):
    p = _icici_sheet(tmp_path, [
        [1, "", "01/10/2026", "", "A", "0", "100", "100"],
        ["x", "", "", "", "stray", "", "", ""],  # non-numeric S No. ends parsing early
        [2, "", "02/10/2026", "", "B", "0", "50", "150"],
    ])
    with pytest.raises(ValueError, match="parsed 1 rows but sheet has 2"):
        icici_bank.parse(p)


# --- SBI bank ---

SBI_HDR = [["Account Statement"], [], ["Date", "Details", "Ref No/Cheque No", "Debit", "Credit", "Balance"]]


def _sbi_sheet(tmp_path, body):
    return _xlsx(tmp_path, SBI_HDR + body + [["Legend: synthetic footer"]])


def test_sbi_bank_rows_amounts_and_wrapped_details(tmp_path):
    p = _sbi_sheet(tmp_path, [
        ["01/10/2026", "UPI/DR/TESTMART", "", "100.00", "", "900.00"],
        [None, "ORDER42", None, None, None, None],
        ["02-10-2026", "SALARY FAKECO", "", "", "1,000.50", "1,900.50"],
    ])
    t = sbi_bank.parse(p)
    assert [(x.date, x.amount, x.description, x.balance_after) for x in t] == [
        (date(2026, 10, 1), D("-100.00"), "UPI/DR/TESTMART ORDER42", D("900.00")),
        (date(2026, 10, 2), D("1000.50"), "SALARY FAKECO", D("1900.50")),
    ]


def test_sbi_bank_early_footer_drops_dated_row_raises(tmp_path):
    p = _sbi_sheet(tmp_path, [
        ["01/10/2026", "A", "", "", "100", "100"],
        ["not a date", "junk", "", "", "", ""],
        ["02/10/2026", "B", "", "", "50", "150"],
    ])
    with pytest.raises(ValueError, match="parsed 1 rows but sheet has 2"):
        sbi_bank.parse(p)


def test_icici_bank_broken_balance_chain_raises(tmp_path):
    p = _icici_sheet(tmp_path, [
        [1, "", "01/10/2026", "", "A", "0", "100", "100"],
        [2, "", "02/10/2026", "", "B", "0", "50", "999"],
    ])
    with pytest.raises(ValueError, match="balance chain"):
        icici_bank.parse(p)


def test_sbi_bank_broken_balance_chain_raises(tmp_path):
    p = _sbi_sheet(tmp_path, [
        ["01/10/2026", "A", "", "", "100", "100"],
        ["02/10/2026", "B", "", "", "50", "999"],
    ])
    with pytest.raises(ValueError, match="balance chain"):
        sbi_bank.parse(p)


SBI_SUMMARY = [["Statement Summary : 01-10-2026 To 02-10-2026"],
               ["Brought Forward (₹)", "Dr Count", "Cr Count", "Total Debits (₹)", "Total Credits (₹)", "Closing Balance (₹)"]]
SBI_ROWS = [["01/10/2026", "UPI/DR/TESTMART", "", "100.00", "", "900.00"],
            ["02/10/2026", "SALARY FAKECO", "", "", "1,000.50", "1,900.50"]]


def _sbi_with_summary(tmp_path, figures):
    return _xlsx(tmp_path, SBI_HDR + SBI_ROWS + [[]] + SBI_SUMMARY + [figures])


def test_sbi_bank_statement_summary_that_matches_passes(tmp_path):
    p = _sbi_with_summary(tmp_path, ["1,000.00CR", "1", "1", "100.00", "1,000.50", "1,900.50CR"])
    assert len(sbi_bank.parse(p)) == 2


@pytest.mark.parametrize("figures,field", [
    (["1,000.00CR", "1", "1", "100.00", "2,000.50", "1,900.50CR"], "credits"),       # a credit row missing
    (["1,000.00CR", "2", "1", "100.00", "1,000.50", "1,900.50CR"], "debit rows"),     # count off
    (["5,000.00CR", "1", "1", "100.00", "1,000.50", "1,900.50CR"], "opening balance"),  # first rows dropped
    (["1,000.00CR", "1", "1", "100.00", "1,000.50", "9,900.50CR"], "closing balance"),  # last rows dropped
])
def test_sbi_bank_statement_summary_mismatch_rejects_the_file(tmp_path, figures, field):
    with pytest.raises(ValueError, match=field) as e:
        sbi_bank.parse(_sbi_with_summary(tmp_path, figures))
    assert "1,000" not in str(e.value) and "900" not in str(e.value)


def test_sbi_bank_ref_is_the_stripped_ref_cell_or_empty(tmp_path):
    p = _sbi_sheet(tmp_path, [["01/10/2026", "UPI/DR/TESTMART", "  TEST000111 ", "100.00", "", "900.00"],
                              ["02-10-2026", "SALARY FAKECO", "", "", "1,000.50", "1,900.50"]])
    assert [t.ref for t in sbi_bank.parse(p)] == ["TEST000111", ""]


def test_icici_bank_ref_is_the_cheque_number_or_empty(tmp_path):
    p = _icici_sheet(tmp_path, [[1, "01/10/2026", "01/10/2026", "000123", "CHQ PAID", "100.00", "0.00", "900.00"],
                                [2, "02/10/2026", "02/10/2026", "", "SALARY FAKECO", "0.00", "1,000.50", "1,900.50"]])
    t = icici_bank.parse(p)
    assert [(x.ref, x.description) for x in t] == [("000123", "CHQ PAID"), ("", "SALARY FAKECO")]


def test_icici_card_csv_ref_is_the_sernum():
    fx = Path(__file__).parent / "fixtures"
    assert {t.ref for t in icici_card.parse(fx / "icici_card_a.csv")} >= {"1001", "1000"}
