"""Reading PDF words (pdfplumber dicts with text/x0/x1/top) by position relative to a printed label."""
import re


def norm(t):
    """Undo fake bold: some layouts print a label with every letter doubled ('SSTTAATTEE'); collapse a word only
    when every pair is doubled, so a genuine word like 'LOOK' is left alone."""
    return t[::2] if len(t) % 2 == 0 and t[::2] == t[1::2] else t


def label(words, *texts):
    """The topmost-leftmost run of consecutive words reading `texts` on one line, as one box {x0, x1, top}; None if absent."""
    n, found = len(texts), []
    for i in range(len(words) - n + 1):
        run = words[i:i + n]
        if [norm(w["text"]) for w in run] == list(texts) and max(w["top"] for w in run) - min(w["top"] for w in run) < 3:
            found.append({"x0": run[0]["x0"], "x1": run[-1]["x1"], "top": run[0]["top"]})
    return min(found, key=lambda b: (b["top"], b["x0"]), default=None)  # topmost, leftmost: "Credit Limit" also sits inside "Available Credit Limit"


def right(words, lab, pattern):
    """Text on the label's own line, to its right, if it fully matches `pattern`; else None."""
    if lab is None:
        return None
    text = " ".join(w["text"] for w in sorted(words, key=lambda w: w["x0"])
                    if abs(w["top"] - lab["top"]) < 3 and w["x0"] >= lab["x1"])
    return text if re.fullmatch(pattern, text) else None


def below(words, lab, pattern, *, reach=45, pad=10):
    """Text of the nearest line under a label (centred within its width ± pad) that fully matches `pattern`,
    skipping lines that don't (a note printed between a label and its figure). None if there is none."""
    if lab is None:
        return None
    near = [w for w in words if 0 < w["top"] - lab["top"] <= reach
            and lab["x0"] - pad <= (w["x0"] + w["x1"]) / 2 <= lab["x1"] + pad]
    lines = []
    for w in sorted(near, key=lambda w: (w["top"], w["x0"])):
        if lines and w["top"] - lines[-1][0] < 3:
            lines[-1][1].append(w)
        else:
            lines.append((w["top"], [w]))
    for _, ws in lines:
        text = " ".join(w["text"] for w in sorted(ws, key=lambda w: w["x0"]))
        if re.fullmatch(pattern, text):
            return text
