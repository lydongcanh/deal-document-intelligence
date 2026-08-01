"""Numbering grammar: parse markers into comparable ordinals and test sequence.

Step 2 of segmentation. This turns a marker's text into a `ParsedMarker` with a
numeric path, and answers the two questions the decoder needs: is B the next
sibling of A (1.1 -> 1.2, (a) -> (b), (ii) -> (iii)), and is B the first child
of A (2 -> 2.1, 1.1 -> 1.1.1). Roman versus alpha ambiguity is resolved by trying
both readings and seeing which one fits the sequence.

Cross-family nesting (Section 2.4 down to its (a), (b) sub-parts) is NOT decided
here, that needs the document-wide stack, which is the decoder's job (step 4).
"""

from __future__ import annotations

import re

from deal_document_intelligence.segmentation.parsed_marker import ParsedMarker

_ROMAN = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}


def parse_roman(s: str) -> int | None:
    """Value of a roman-numeral string, or None if it is not roman."""
    s = s.lower()
    if not s or any(ch not in _ROMAN for ch in s):
        return None

    total, prev = 0, 0
    for ch in reversed(s):
        val = _ROMAN[ch]
        total += -val if val < prev else val
        prev = max(prev, val)

    return total


def alpha_value(s: str) -> int | None:
    """Position of a single letter (a=1 .. z=26), or None. Doubles handled later."""
    if len(s) == 1 and s.isalpha():
        return ord(s.lower()) - ord("a") + 1

    return None


def _roman_or_int(token: str) -> int | None:
    if token.isdigit():
        return int(token)

    return parse_roman(token)


def parse_marker(family: str, marker_text: str) -> ParsedMarker:
    text = marker_text.strip()

    if family == "article":
        n = _roman_or_int(text.split()[-1])  # "ARTICLE III" -> "III"
        return ParsedMarker(family=family, path=(n,) if n else ())

    if family in ("section", "hier-decimal", "decimal"):
        nums = re.findall(r"\d+", text)  # "Section 7.2"/"7.2." -> ["7","2"]
        return ParsedMarker(family=family, path=tuple(int(x) for x in nums))

    if family == "paren-num":
        nums = re.findall(r"\d+", text)
        return ParsedMarker(family=family, path=(int(nums[0]),) if nums else ())

    inner = text.strip("()").strip()  # "(b)" -> "b"
    if family == "paren-upper":
        v = alpha_value(inner)
        return ParsedMarker(family=family, path=(v,) if v else ())

    # paren-lower: ambiguous. Prefer alpha for a single letter, keep the roman
    # reading as the alternative; fall back to roman for multi-letter tokens.
    alpha = alpha_value(inner)
    roman = parse_roman(inner)
    if alpha is not None:
        return ParsedMarker(
            family=family,
            path=(alpha,),
            alt_path=(roman,) if roman is not None else None,
        )

    return ParsedMarker(family=family, path=(roman,) if roman is not None else ())


def _readings(m: ParsedMarker) -> list[tuple[int, ...]]:
    return [p for p in (m.path, m.alt_path) if p]


def is_sibling_successor(a: ParsedMarker, b: ParsedMarker, max_skip: int = 0) -> bool:
    """True if b continues a's sibling sequence (same depth, same prefix).

    max_skip tolerates that many dropped ordinals, so with max_skip=1 both
    1.1 -> 1.2 and 1.1 -> 1.3 (a missing 1.2) count. The default is strict (+1)."""
    for pa in _readings(a):
        for pb in _readings(b):
            if (len(pa) == len(pb) >= 1 and pa[:-1] == pb[:-1]
                    and 1 <= pb[-1] - pa[-1] <= 1 + max_skip):
                return True

    return False


def is_child_start(a: ParsedMarker, b: ParsedMarker) -> bool:
    """True if b is the first child of a within the same numbering family
    (2 -> 2.1, 1.1 -> 1.1.1). Cross-family nesting is the decoder's job."""
    for pa in _readings(a):
        for pb in _readings(b):
            if len(pb) == len(pa) + 1 and pb[:-1] == pa and pb[-1] == 1:
                return True

    return False


def starts_sequence(m: ParsedMarker) -> bool:
    """True if the marker is the first in its sequence (ordinal 1), for example
    (a), (i), (1), 2.1. Used to open a fresh sub-list under the current clause."""
    return any(p and p[-1] == 1 for p in _readings(m))
