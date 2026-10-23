# /// script
# requires-python = ">=3.11"
# dependencies = ["indian-finance-parsers[all]>=0.1", "faker>=40.43", "gliner>=0.2.29", "beautifulsoup4", "lxml"]
# ///
"""Print a document's text with personal data swapped for realistic fakes, so Claude can write a parser from it.

Labels, wording, amounts, dates and layout stay verbatim; names, addresses, ids and account/card/phone numbers get
same-length fakes, the same fake for the same original throughout the file. Three layers:
  (a) a denylist, the hard backstop (read here, never printed): ~/.config/infinparse/denylist.txt, or the file
      $INFINPARSE_DENYLIST names; one term per line, # comments;
  (b) regexes for ids and numbers (PAN, Aadhaar, IFSC, card, account, phone, email, UPI, PIN code);
  (c) NER for names and addresses (GLiNER by default; --ner ollama|none).
Nothing is printed if any denylist term survives. Decrypted text stays in memory.
The output is still personal data (amounts, dates, merchants): never paste it into an issue, PR or test fixture.
Run: uv run tools/anonymise.py FILE [PASSWORD_ENV] [--ner gliner|ollama|none]
  PASSWORD_ENV names the environment variable holding an encrypted file's password, e.g.
  uv run --env-file ../finance-fix/.env tools/anonymise.py statement.pdf HDFC_CARD_PASSWORD
"""
import io
import json
import os
import random
import re
import sys
import urllib.request
import zipfile
from functools import cache
from pathlib import Path

DENYLIST = Path(os.environ.get("INFINPARSE_DENYLIST") or Path.home() / ".config/infinparse/denylist.txt")
GLINER_MODEL = "knowledgator/gliner-pii-base-v1.0"
GLINER_REVISION = "61726e0ad791dcab3e29339bbec3ad42ded65641"  # pinned: the commit the eval ran on
GLINER_LABELS = {"person": "name", "name": "name", "full name": "name", "nominee": "name", "holder": "name",
                 "address": "address"}  # this set at 0.2 leaked least on the eval (docs/anonymiser.md)
GLINER_THRESHOLD = 0.2
OLLAMA_MODEL = "qwen3-coder:30b"  # gemma4:e4b-mlx-bf16 fails to load in this ollama (mlx runner exits)


# ---- extraction -------------------------------------------------------------------------------------------------


def _table(df):
    return "\n".join(" | ".join("" if str(c) == "nan" else str(c) for c in row) for row in df.itertuples(index=False))


def extract(name, data) -> str:
    """Text of one file (name, bytes). PDFs keep their layout (layout=True pads words to their x position)."""
    ext = Path(name).suffix.lower()
    if ext == ".pdf":
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join(f"--- page {i} ---\n{p.extract_text(layout=True)}" for i, p in enumerate(pdf.pages, 1))
    if ext in (".xls", ".xlsx"):
        import pandas as pd
        try:
            sheets = pd.read_excel(io.BytesIO(data), header=None, dtype=str, sheet_name=None)
        except Exception:  # some banks ship HTML named .xls
            sheets = dict(enumerate(pd.read_html(io.BytesIO(data), header=None)))
        return "\n".join(f"--- sheet {k} ---\n{_table(df)}" for k, df in sheets.items())
    if ext in (".html", ".htm"):
        from bs4 import BeautifulSoup
        text = BeautifulSoup(data, "lxml").get_text("\n")
        return "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if ext == ".zip":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            return "\n".join(f"=== {m} ===\n{extract(m, z.read(m))}" for m in z.namelist() if not m.endswith("/"))
    return data.decode("utf-8", errors="replace")  # csv, json, txt


def read(path, password_env=None) -> str:
    path = Path(path)
    if password_env:
        from indian_finance_parsers.decrypt import decrypted
        f = decrypted(path, os.environ[password_env])
        data = f.getvalue() if isinstance(f, io.BytesIO) else path.read_bytes()
    else:
        data = path.read_bytes()
    return f"file: {path.name}\n{extract(path.name, data)}"  # names in done/ carry card digits: anonymised too


# ---- fakes ------------------------------------------------------------------------------------------------------


@cache
def dictionary():
    """Lowercase English words: an NER hit made only of these is a label ("Interest Frequency"), not a name."""
    try:
        with open("/usr/share/dict/words") as f:
            return frozenset(w.strip() for w in f if w.strip().islower())
    except OSError:
        return frozenset()


@cache
def name_pool():
    """Indian first/last names and city words by length, for same-length fakes."""
    from faker import Faker
    fake = Faker("en_IN")
    fake.seed_instance(0)
    pool = {}
    for _ in range(3000):
        for w in (fake.first_name(), fake.last_name(), fake.city()):
            for part in re.findall(r"[A-Za-z]+", w):
                pool.setdefault(len(part), set()).add(part.lower())
    return {n: sorted(ws) for n, ws in pool.items()}


def _case_like(src, fake):
    if src.isupper():
        return fake.upper()
    if src[:1].isupper():
        return fake.capitalize()
    return fake.lower()


class Faker:
    """Same-length, same-shape fakes, the same one for the same original (case-insensitive) within a file."""

    def __init__(self, seed=0):
        self.rnd, self.seen = random.Random(seed), {}

    def word(self, w):
        if (key := w.lower()) not in self.seen:
            pool = name_pool().get(len(w)) or [self.rnd.choice(name_pool()[max(name_pool())])[: len(w)]]
            fakes = [c for c in pool if c != key and not any(t in c for t in _deny_words())]
            if not fakes:  # no other word that long: random letters rather than the original
                return self.chars(w)
            self.seen[key] = self.rnd.choice(fakes)
        if self.seen[key] == key:  # chars() already stored this one
            return self.chars(w)
        return _case_like(w, self.seen[key])

    def chars(self, s):
        """Digits -> digits, letters -> letters, keeping mask runs (XXXX, ****) and punctuation."""
        if (key := s.lower()) not in self.seen:
            out = []
            for i, c in enumerate(s):
                masked = c in "Xx*" and (s[i - 1:i] in ("X", "x", "*") or s[i + 1:i + 2] in ("X", "x", "*"))
                if c.isdigit():
                    out.append(str(self.rnd.randrange(1 if i == 0 else 0, 10)))
                elif c.isalpha() and not masked:
                    out.append(self.rnd.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
                else:
                    out.append(c)
            self.seen[key] = "".join(out)
        return "".join(f.lower() if c.islower() else f for c, f in zip(s, self.seen[key], strict=True))

    def text(self, s):
        """Alphabetic tokens -> name-like words, everything else char by char."""
        return re.sub(r"[A-Za-z]+|[^A-Za-z]+", lambda m: self.word(m[0]) if m[0].isalpha() and len(m[0]) > 1
                      else self.chars(m[0]), s)


# ---- detection --------------------------------------------------------------------------------------------------


@cache
def _deny_words():
    """Lowercase denylist words, so no fake happens to be one (the guard would then refuse the file every run)."""
    return frozenset(w.lower() for t, _ in denylist() for w in t.split() if w.isalpha())


def flexible(term):
    """Regex for a term that tolerates layout: any whitespace run where it has one, an optional space/hyphen between
    digit groups (a card or phone number printed in blocks)."""
    out = []
    for i, c in enumerate(term):
        if c.isspace():
            if out and out[-1] != r"\s+":
                out.append(r"\s+")
        else:
            out.append(re.escape(c))
            if c.isdigit() and term[i + 1:i + 2].isdigit():
                out.append(r"[ -]?")
    return "".join(out)


@cache
def denylist():
    """Compiled denylist terms; the file is read here only, never printed."""
    try:
        terms = [t.strip() for t in DENYLIST.read_text().splitlines()]
    except OSError:
        sys.exit(f"anonymise: {DENYLIST} not readable; refusing to run without the backstop")
    out = [(t, re.compile(flexible(t), re.I)) for t in terms if t and not t.startswith("#")]
    if not out:
        sys.exit(f"anonymise: {DENYLIST} has no terms; refusing to run without the backstop")
    return out


def leaks(text):
    """How many denylist terms appear in text: pii_check's rule (case-insensitive substring) plus layout tolerance."""
    low = text.lower()
    return sum(1 for t, rx in denylist() if t.lower() in low or rx.search(text))


NUM = r"(?<![\d.])(?<!\d,)"  # not inside an amount (a CSV comma before a number is fine)
REGEXES = {  # kind -> pattern; amounts (with , or .) and dates (with / - or month names) never match
    "email/upi": r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*",
    "pan": r"\b[A-Z]{5}\d{4}[A-Z]\b",
    "ifsc": r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
    "card": r"(?<![^\W_])\d{4,6}[ -]?[Xx*]{2,}[ Xx*-]*\d{2,4}(?![^\W_])|\b[Xx*]{4,}[ -]?\d{4}(?![^\W_])",
    "aadhaar": NUM + r"\b\d{4} \d{4} \d{4}\b(?!\d|\.\d)",
    "phone": r"\+91[ -]?\d{5}[ -]?\d{5}\b|" + NUM + r"\b[6-9]\d{4} \d{5}\b(?!\d|\.\d)",
    "number": NUM + r"(?<![^\W_])\d{9,19}(?![^\W_]|\.\d)",  # account, card, phone, customer/ref ids
    "id": r"\b(?=[A-Z0-9]*\d)(?=[A-Z0-9]*[A-Z])[A-Z0-9]{10,}\b",  # mixed alnum ids (CRN, folio); ISINs too
    "pin": r"(?i)(?<=pin)(?:\s*code)?\s*[:-]?\s*[1-9]\d{2} ?\d{3}\b|(?<=[,-] )[1-9]\d{5}\b(?!\d|\.\d)",
}
COMPILED = {k: re.compile(v) for k, v in REGEXES.items()}
ISIN = re.compile(r"^IN[EF][A-Z0-9]{8}\d$")  # public security ids a parser needs


def chunks(text, size):
    """Whitespace-collapsed pieces of about size chars, split at line ends."""
    buf = ""
    for line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        if buf and len(buf) + len(line) > size:
            yield buf
            buf = ""
        buf += line + "\n"
    if buf:
        yield buf


def ner_gliner(text):
    model, found = _gliner(GLINER_MODEL), []
    for chunk in chunks(text, 1000):  # GLiNER reads ~384 tokens at a time
        found += [(GLINER_LABELS[e["label"]], e["text"])
                  for e in model.predict_entities(chunk, list(GLINER_LABELS), threshold=GLINER_THRESHOLD)]
    return found


@cache
def _gliner(name):
    from gliner import GLiNER
    return GLiNER.from_pretrained(name, revision=GLINER_REVISION)


def ner_ollama(text, model=OLLAMA_MODEL):
    found = []
    for chunk in chunks(text, 6000):
        prompt = ("List every person's name and every postal address (street, locality, city, PIN) in the "
                  "document below. Copy each exactly as written. Do not list companies, banks, merchants or "
                  'field labels. Answer JSON: {"names": [...], "addresses": [...]}\n\n' + chunk)
        req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=json.dumps(
            {"model": model, "prompt": prompt, "format": "json", "stream": False,
             "options": {"temperature": 0}}).encode())
        out = json.loads(json.loads(urllib.request.urlopen(req, timeout=600).read())["response"] or "{}")
        for kind, key in (("name", "names"), ("address", "addresses")):
            found += [(kind, s) for s in out.get(key, []) if isinstance(s, str) and s.strip()
                      and re.search(flexible(s.strip()), chunk, re.I)]  # only spans really in the text
    return found


NER = {"gliner": ner_gliner, "ollama": ner_ollama, "none": lambda text: []}


# ---- replacement ------------------------------------------------------------------------------------------------


def anonymise(text, ner="gliner", use_denylist=True, stats=None):
    """text with personal data replaced. stats (a dict) collects counts per layer."""
    fake, spans = Faker(), []  # (start, end, replacement-fn)
    stats = {} if stats is None else stats

    def add(rx, fn, kind):
        for m in rx.finditer(text):
            spans.append((m.start(), m.end(), fn))
            stats[kind] = stats.get(kind, 0) + 1

    if use_denylist:
        for _, rx in denylist():
            add(rx, fake.text, "denylist")
    for kind, rx in COMPILED.items():
        add(rx, (lambda s: s if ISIN.match(s) else fake.chars(s)) if kind == "id" else fake.chars, kind)
    words = dictionary()
    name_tokens = set()
    for kind, s in NER[ner](text):
        toks = re.findall(r"[A-Za-z]+", s)
        if not toks or (all(t.lower() in words or len(t) < 3 for t in toks) and not re.search(r"\d", s)):
            continue  # a label or a fragment, not a name
            # ponytail: a name made only of dictionary words ("Grace Hill") is skipped too; only the denylist catches it
        if kind == "name":
            name_tokens |= {t.lower() for t in toks if t.lower() not in words and len(t) > 2}
        add(re.compile(flexible(s.strip()), re.I), fake.text, f"ner-{kind}")
    if name_tokens:  # a name found once is replaced wherever it recurs, e.g. alone in a table
        add(re.compile(r"\b(?:" + "|".join(map(re.escape, sorted(name_tokens, key=len, reverse=True))) + r")\b",
                       re.I), fake.text, "ner-name-token")
    out, pos = [], 0
    for start, end, fn in sorted(spans, key=lambda s: (s[0], -s[1])):  # earliest, then longest, wins
        if start < pos:
            if end > pos:  # overlaps the previous span: fake the rest char by char
                out.append(fake.chars(text[pos:end]))
                pos = end
            continue
        out += [text[pos:start], fn(text[start:end])]
        pos = end
    return "".join(out) + text[pos:]


def main(argv):
    ner = "gliner"
    if "--ner" in argv:
        i = argv.index("--ner")
        ner, argv = argv[i + 1], argv[:i] + argv[i + 2:]
    if not argv:
        sys.exit(__doc__)
    out = anonymise(read(argv[0], argv[1] if len(argv) > 1 else None), ner)
    if n := leaks(out):
        sys.exit(f"anonymise: {n} denylist term(s) survived; nothing printed")
    print(out)


if __name__ == "__main__":
    main(sys.argv[1:])
