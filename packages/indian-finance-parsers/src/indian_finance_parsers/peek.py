"""Print a statement's structure with all personal data masked, so a parser can be written without seeing it.

Words outside a small header vocabulary become X/x, digits become 9. Punctuation, layout and
column positions are kept. Run: python -m indian_finance_parsers.peek FILE [rows]  (needs the `excel` extra)
"""
import re
import sys
import unicodedata

import pandas as pd

VOCAB = set("""date value transaction txn tran posting description details narration particulars remarks
remark merchant amount amt debit credit withdrawal deposit balance dr cr inr rs type mode ref reference
no number chq cheque sr s id card points reward total opening closing statement category""".split())


def mask(cell) -> str:
    if pd.isna(cell):
        return ""
    s = str(cell)
    s = re.sub(r"[^\W\d_]+", lambda m: m.group() if m.group().lower() in VOCAB else  # any script's letters
               "".join("X" if c.isupper() else "x" for c in m.group()), s)
    s = "".join("x" if ord(c) > 127 and unicodedata.category(c)[0] in "LM" else c for c in s)  # e.g. Devanagari vowel signs
    return re.sub(r"\d", "9", s)


def read(path):
    if path.lower().endswith((".xls", ".xlsx")):
        try:
            return pd.read_excel(path, header=None, dtype=str)
        except Exception:
            return pd.read_html(path, header=None)[0].astype(str)  # some banks ship HTML named .xls
    return pd.read_csv(path, header=None, dtype=str, sep=None, engine="python",
                       on_bad_lines="skip", encoding_errors="replace")


if __name__ == "__main__":
    path, n = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 25
    df = read(path)
    print(f"{mask(path.split('/')[-1])}: {df.shape[0]} rows x {df.shape[1]} cols")  # names carry card digits
    for i, row in df.head(n).iterrows():
        print(i, " | ".join(mask(c) for c in row))
