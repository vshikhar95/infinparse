"""Linear-time HTML helpers for saved pages. Store pages are untrusted input, so no pattern here may backtrack
across the file (a regex like `<tr.*?</tr>` rescans to the end from every `<tr` when the closing tag is missing)."""
import re

TAG = re.compile(r"<[^<>]*>")  # stops at the next '<', so an unclosed '<' costs nothing


def blocks(html, tag):
    """[(opening tag, inner html)] for every <tag ...>...</tag>, by splitting on the closing tag."""
    out = []
    for chunk in html.split(f"</{tag}>")[:-1]:  # the last piece has no closing tag
        start = chunk.rfind(f"<{tag}")
        end = chunk.find(">", start)
        if start != -1 and end != -1:
            out.append((chunk[start:end + 1], chunk[end + 1:]))
    return out


def drop(html, tag):
    """html without any <tag>...</tag> blocks (an unclosed one is dropped to the end)."""
    out, pos = [], 0
    while (start := html.find(f"<{tag}", pos)) != -1:
        out.append(html[pos:start])
        end = html.find(f"</{tag}>", start)
        pos = len(html) if end == -1 else end + len(tag) + 3
    out.append(html[pos:])
    return "".join(out)
