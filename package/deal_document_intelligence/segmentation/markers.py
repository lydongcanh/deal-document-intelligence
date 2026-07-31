"""Legal numbering markers: the patterns that MIGHT begin a clause.

A match here is a *possible* marker, not a boundary. "See Section 4.2", "1.5%",
and "dated 1.1.2026" all match something, and none starts a clause. Deciding
which matches are real boundaries is the job of the numbering grammar and the
constrained decoder (later steps), not this module. Here we cast a wide,
high-recall net and keep exact positions.

We deliberately do not try to tell roman from alpha here (is "(i)" the letter i
or roman one?). That is a document-level decision the grammar makes from the
surrounding sequence, so both fall under `paren-lower`.
"""

from __future__ import annotations

import re

# (family, compiled pattern). Order is priority: when two patterns match at the
# same position, the earlier family wins. More specific patterns come first.
MARKER_FAMILIES: list[tuple[str, re.Pattern[str]]] = [
    ("article", re.compile(r"ARTICLE\s+(?:[IVXLC]+|\d+)", re.IGNORECASE)),
    ("section", re.compile(r"(?:Section|Clause)\s+\d+(?:\.\d+)*", re.IGNORECASE)),
    (
        "region",
        re.compile(
            r"(?:Schedule|Annex(?:ure)?|Exhibit|Appendix)\s+(?:[A-Z]+|\d+)",
            re.IGNORECASE,
        ),
    ),
    ("hier-decimal", re.compile(r"\d+(?:\.\d+)+\.?")),  # 1.1  1.1.1  7.2.
    ("decimal", re.compile(r"\d+\.(?=\s)")),  # 1.  2.  (dot then space)
    ("paren-lower", re.compile(r"\([a-z]{1,3}\)")),  # (a) (i) (iv) (aa)
    ("paren-upper", re.compile(r"\([A-Z]{1,3}\)")),  # (A) (IV)
    ("paren-num", re.compile(r"\(\d+\)")),  # (1) (2)
]


def scan(text: str) -> list[tuple[str, str, int, int]]:
    """Find non-overlapping markers in `text`.

    Returns (family, marker_text, start, end) tuples, left to right.
    Overlaps are resolved by earliest start, then family priority above.
    """
    raw: list[tuple[int, int, str, str, int]] = []
    for priority, (family, pattern) in enumerate(MARKER_FAMILIES):
        for m in pattern.finditer(text):
            raw.append((m.start(), priority, family, m.group(), m.end()))

    raw.sort()

    out: list[tuple[str, str, int, int]] = []
    last_end = -1
    for start, _priority, family, marker_text, end in raw:
        if start >= last_end:  # keep non-overlapping, first by (start, priority)
            out.append((family, marker_text, start, end))
            last_end = end

    return out
