# Anonymiser: reading a real document to write its parser

`tools/anonymise.py` prints a document's text with names, addresses, ids and account, card and phone numbers swapped
for realistic fakes of the same length and shape. Labels, wording, amounts, dates and layout come through as printed,
so you (or a coding agent) can write a parser against the real layout. `peek` masks every non-header word instead,
which can hide the labels a parser anchors on ("Interest Xxxxxxxxx"); it needs no model, so try it first.

**The output is still personal data.** Amounts, dates and merchants are kept. Read it locally; never paste it into an
issue, pull request, test fixture or a hosted chat.

## Run

```bash
uv run tools/anonymise.py statement.pdf                    # dependencies install on first run (torch, ~2 GB)
uv run --env-file path/to/.env tools/anonymise.py statement.pdf HDFC_CARD_PASSWORD   # encrypted: names the variable
uv run tools/anonymise.py statement.pdf --ner ollama       # second opinion from a local model (slower)
```

Reads PDF (with layout), xlsx/xls (including HTML saved as .xls), csv/json/txt, html and zip. Encrypted files are
decrypted in memory. The first run downloads the GLiNER model (`knowledgator/gliner-pii-base-v1.0`, pinned to one
revision, 1.7 GB) from Hugging Face; documents never leave the machine.

## The denylist (required)

One term per line in `~/.config/infinparse/denylist.txt` (or the file `$INFINPARSE_DENYLIST` names): your name and
family members' names, address lines, PAN, account, card and phone numbers. The tool refuses to run without it, and
prints nothing if any term survives in its output. It is the only layer that is never wrong, so list everything you
would not want seen. Keep it outside the repository.

## Layers

1. **Denylist:** every occurrence, whatever the case, spacing or hyphens.
2. **Regexes:** email/UPI, PAN, IFSC, masked cards, Aadhaar, +91 phones, bare 9-19 digit runs, mixed alphanumeric ids of
   10+ characters (ISINs are kept), PIN codes. Digits inside amounts are never touched.
3. **NER (GLiNER):** person names, nominees and addresses. A name found once is replaced wherever it recurs.

Fakes keep their length, so columns don't shift; the same original gets the same fake throughout a file.

## Known limits

- A name made only of dictionary words ("Grace Hill") is skipped by NER as if it were a label. Only the denylist
  catches it, so a third party (a nominee, a UPI payee) with such a name can pass through. Measured on six real
  documents (two card PDFs, an FD receipt, an SGB certificate, a savings sheet, a holdings sheet): 105 hits were kept
  this way, almost all fund and stock names; 2 were personal (one UPI id, one friend's name); the fix is to add such names to the
  denylist. Look at the output of each new document type yourself before relying on it.
- NER over-replaces: some merchant words and stock names get fakes too.
- IFSC codes and card BINs become fakes, so the branch or issuer can't be read from them.
- No word coordinates: PDFs come out as layout text, not pdfplumber's x/y positions.
