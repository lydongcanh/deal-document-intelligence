"""Score the clause segmenter against the dev/acceptance labels.

Honest scope: this is NOT a golden benchmark. The labels cover a narrow slice
(US SEC merger/SPA filings, born-digital, English) and are derived from each
document's own table of contents, which is independent of the segmenter (it
parses the body, not the TOC). We compare at the section level (Article and N.M).

This measures whether we recovered the right SET of sections. It does not fully
capture hierarchy or position errors (a section found at the wrong place still
counts as found), so read it alongside the coverage measurement.

Usage:
    python eval/clause_segmentation/score.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "demo"))
from docling_parser import DoclingParser  # noqa: E402

from deal_document_intelligence.segmentation import ClauseSegmenter  # noqa: E402
from deal_document_intelligence.segmentation.numbering import parse_roman  # noqa: E402

GOLD_DIR = Path(__file__).parent / "gold"
DOCS = REPO / "demo" / "documents"


def _norm(number: str) -> tuple:
    """Normalise a clause number so gold and prediction compare regardless of
    surface form: "Section 1.1" and "1.1" match; "ARTICLE I" matches by value."""
    t = number.strip()
    if t.upper().startswith("ARTICLE"):
        tok = t.split()[-1]
        return ("ART", int(tok) if tok.isdigit() else parse_roman(tok))
    m = re.search(r"\d+(?:\.\d+)*", t)
    return ("SEC", m.group(0)) if m else ("RAW", t)


def _sections(clauses: list[dict]) -> dict:
    """Normalised key -> (display number, depth), for articles and sections."""
    return {_norm(c["number"]): (c["number"], c["depth"])
            for c in clauses if c["depth"] <= 1}


def score_file(path: Path) -> None:
    gold = json.loads(path.read_text())
    page_range = tuple(gold["page_range"]) if gold.get("page_range") else None
    doc = DoclingParser(page_range=page_range).parse(DOCS / gold["source"])
    units = ClauseSegmenter().segment(doc)

    pred = {_norm(u.number): (u.number, u.meta.get("depth", 9))
            for u in units if u.number and u.meta.get("depth", 9) <= 1}
    want = _sections(gold["clauses"])

    matched = set(want) & set(pred)
    missed = sorted(want[k][0] for k in set(want) - set(pred))
    extra = sorted(pred[k][0] for k in set(pred) - set(want))
    wrong_depth = sorted(want[k][0] for k in matched if pred[k][1] != want[k][1])
    recall = len(matched) / len(want) if want else 0.0
    precision = len(matched) / (len(matched) + len(extra)) if (matched or extra) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    print(f"\n=== {gold['source']}  (pages {gold.get('page_range', 'all')}) ===")
    print(f"labelled sections: {len(want)}   found: {len(matched)}")
    print(f"recall: {recall:.2f}   precision: {precision:.2f}   F1: {f1:.2f}   "
          "(precision assumes gold is complete for the scored range)")
    if missed:
        print(f"  MISSED (labelled but not found): {missed}")
    if wrong_depth:
        print(f"  WRONG DEPTH: {wrong_depth}")
    if extra:
        print(f"  EXTRA predicted (not in gold): {extra}")


def main() -> None:
    files = sorted(GOLD_DIR.rglob("*.json"))
    if not files:
        print(f"no label files in {GOLD_DIR}")
        return
    for path in files:
        score_file(path)


if __name__ == "__main__":
    main()
