"""Build a segmentation gold file from a document's own table of contents.

The TOC is the drafter's authoritative list of articles and sections. It is
independent of our segmenter (which parses the body and skips the TOC), so it is
a legitimate, non-circular source of ground truth at the section level.

Handles the common conventions seen across the corpus:
    articles roman ("ARTICLE I") or arabic ("ARTICLE 1"),
    sections "1.1 ..." or "Section 1.1 ...",
    page references "A-3" or a plain number ("15"),
and stops at the body (a section line with no trailing page reference).

Usage:
    python eval/clause_segmentation/build_gold_from_toc.py <source-under-demo-docs> [out.json]

Not every TOC parses (layouts vary); verify the result against the PDF.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pypdfium2 as pdfium

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / "demo" / "documents"
GOLD = Path(__file__).parent / "gold"

# Match only the marker head; the remainder is taken by slicing (avoids the
# greedy-tail patterns that backtrack).
ART = re.compile(r"^ARTICLE\s+(\S+)", re.IGNORECASE)
SEC = re.compile(r"^(?:Section\s+)?(\d+\.\d+)\.?", re.IGNORECASE)
ROMAN_OR_INT = re.compile(r"[IVXLC]+|\d+", re.IGNORECASE)
PAGE_REF = re.compile(r"A-\w+|\d+", re.IGNORECASE)  # matched against the last token only


def _split_page_ref(rest: str) -> tuple[str, bool]:
    """Strip a trailing page-reference token; return (text, had_ref)."""
    text = rest.strip()
    parts = text.rsplit(" ", 1)
    if len(parts) == 2 and PAGE_REF.fullmatch(parts[1]):
        return parts[0].strip(), True
    return text, False


def _classify_section(line: str) -> tuple[str, str, str] | None:
    """Return (number, heading, kind) where kind is 'toc' or 'body', or None.

    A number with no trailing text is a TOC entry from a two-column layout (the
    numbers are one column, the titles another). A number followed by a page ref
    is a normal TOC entry. A number followed by prose is the body starting.
    """
    m = SEC.match(line)
    if not m:
        return None
    rest = line[m.end():].strip()
    if not rest:
        return m.group(1), "", "toc"
    heading, had_ref = _split_page_ref(rest)
    return m.group(1), heading, ("toc" if had_ref else "body")


def _as_article(line: str) -> tuple[str, str] | None:
    m = ART.match(line)
    if not m:
        return None
    token = m.group(1).rstrip(".")
    if not ROMAN_OR_INT.fullmatch(token):
        return None
    heading, _ = _split_page_ref(line[m.end():])
    return f"ARTICLE {token.upper()}", heading


def _consume(line: str, clauses: list[dict], seen: set, in_toc: bool) -> tuple[bool, bool]:
    """Fold one line into the collection. Returns (in_toc, stop)."""
    sec = _classify_section(line)
    if sec:
        num, heading, kind = sec
        if kind == "body":
            return in_toc, in_toc  # a section with prose (not a page ref) = body has begun
        if ("s", num) not in seen:
            seen.add(("s", num))
            clauses.append({"number": num, "depth": 1, "heading": heading})
        return True, False
    art = _as_article(line)
    if art and ("a", art[0]) not in seen:
        seen.add(("a", art[0]))
        clauses.append({"number": art[0], "depth": 0, "heading": art[1]})
    return in_toc, False


def build(source_rel: str) -> dict:
    pdf = pdfium.PdfDocument(str(DOCS / source_rel))
    clauses: list[dict] = []
    seen: set = set()
    in_toc = False
    for i in range(len(pdf)):
        for raw in pdf[i].get_textpage().get_text_range().splitlines():
            in_toc, stop = _consume(raw.strip(), clauses, seen, in_toc)
            if stop:
                pdf.close()
                return _wrap(source_rel, clauses)
    pdf.close()
    return _wrap(source_rel, clauses)


def _wrap(source_rel: str, clauses: list[dict]) -> dict:
    return {
        "source": source_rel,
        "page_range": None,
        "note": "Derived from the document's own table of contents (independent of the "
                "segmenter, which parses the body). Section level (Article + N.M). "
                "Verify against the PDF.",
        "clauses": clauses,
    }


def main() -> None:
    source_rel = sys.argv[1]
    if len(sys.argv) > 2:
        out = Path(sys.argv[2])
    else:
        stem = Path(source_rel).name.rsplit(".", 1)[0].lower().replace(" ", "_")
        out = GOLD / Path(source_rel).parent / (stem + ".json")
    out.parent.mkdir(parents=True, exist_ok=True)
    data = build(source_rel)
    out.write_text(json.dumps(data, indent=2))
    arts = sum(1 for c in data["clauses"] if c["depth"] == 0)
    secs = sum(1 for c in data["clauses"] if c["depth"] == 1)
    print(f"{out.relative_to(GOLD)}: {arts} articles, {secs} sections")


if __name__ == "__main__":
    main()
