"""Reading PDF words (pdfplumber dicts with text/x0/x1/top) by position relative to a printed label."""
import re


def read(name, field, fn, *args):
    """fn(*args), where a failure to parse raises "<name>: <field> is unreadable": the parser's own message would
    quote the value, and exceptions end up in logs."""
    try:
        return fn(*args)
    except (ValueError, ArithmeticError):
        raise ValueError(f"{name}: {field} is unreadable") from None


def norm(t):
    """Undo fake bold: some layouts print a label with every letter doubled ('SSTTAATTEE'); collapse a word only
    when every pair is doubled, so a genuine word like 'LOOK' is left alone."""
    return t[::2] if len(t) % 2 == 0 and t[::2] == t[1::2] else t


def label(words, *texts):
    """The topmost-leftmost run of consecutive words reading `texts` on one line, as one box {x0, x1, top}; None if absent."""
    n, found = len(texts), []
    for i in range(len(words) - n + 1):
        run = words[i:i + n]
        if i and norm(words[i - 1]["text"]) == "Available" and abs(words[i - 1]["top"] - run[0]["top"]) < 3:
            continue  # "Credit Limit" inside "Available Credit Limit" is another label
        if [norm(w["text"]) for w in run] == list(texts) and max(w["top"] for w in run) - min(w["top"] for w in run) < 3:
            found.append({"x0": run[0]["x0"], "x1": run[-1]["x1"], "top": run[0]["top"]})
    return min(found, key=lambda b: (b["top"], b["x0"]), default=None)


def right(words, lab, pattern):
    """Text on the label's own line, to its right, if it fully matches `pattern`; else None."""
    if lab is None:
        return None
    text = " ".join(w["text"] for w in sorted(words, key=lambda w: w["x0"])
                    if abs(w["top"] - lab["top"]) < 3 and w["x0"] >= lab["x1"])
    return text if re.fullmatch(pattern, text) else None


def below(words, lab, pattern, *, reach=45, pad=10, skip=None):
    """Text of the first line under a label (more than 3 pt lower, so same-line jitter doesn't count; words centred
    within the label's width ± pad) if it fully matches `pattern`; None if it doesn't. It never falls through to a
    later row's figure. `skip`: a pattern for note lines that legitimately sit between a label and its figure
    (HDFC prints "(Including Cash)" under TOTAL CREDIT LIMIT); matching lines are passed over."""
    if lab is None:
        return None
    near = [w for w in words if 3 < w["top"] - lab["top"] <= reach
            and lab["x0"] - pad <= (w["x0"] + w["x1"]) / 2 <= lab["x1"] + pad]
    lines = []
    for w in sorted(near, key=lambda w: (w["top"], w["x0"])):
        if lines and w["top"] - lines[-1][0] < 3:
            lines[-1][1].append(w)
        else:
            lines.append((w["top"], [w]))
    for _, ws in lines:
        text = " ".join(w["text"] for w in sorted(ws, key=lambda w: w["x0"]))
        if skip and re.fullmatch(skip, text):
            continue
        return text if re.fullmatch(pattern, text) else None
