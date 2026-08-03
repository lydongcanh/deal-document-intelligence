"""Held-out generalisation check for the deterministic segmenter.

These documents are OTHER contract types (material contracts, equity/comp
agreements, a charter) from public SEC filings, never used to tune the segmenter.
There is no section gold, so this is a gold-free health + router check, scored
ONCE, no tuning:

- structural health: validation invariants (source-aligned, monotonic,
  child-in-parent, text conservation), clause/article counts, max depth, and
  documents that come back empty;
- router: the confidence score and whether the gate would escalate, so we can see
  whether the fail-safe fires on the documents where segmentation looks poor.

Run:  poetry run python eval/clause_segmentation/heldout.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "demo"))
from docling_parser import DoclingParser  # noqa: E402

from deal_document_intelligence.contracts import ClauseRole, ParsedDocument  # noqa: E402
from deal_document_intelligence.segmentation import (  # noqa: E402
    DeterministicClauseSegmenter,
    clause_tree,
    validate_tree,
)

DOCS = REPO / "demo" / "documents"
FOLDERS = ["material_contracts", "equity_compensation", "charter_bylaws"]
CACHE = REPO / "artifacts" / "cache" / "parsed"


def _parse_cached(path: Path) -> ParsedDocument:
    key = CACHE / (path.stem + ".json")
    if key.exists():
        return ParsedDocument.model_validate_json(key.read_text())
    doc = DoclingParser().parse(path)
    key.parent.mkdir(parents=True, exist_ok=True)
    key.write_text(doc.model_dump_json())
    return doc


def main() -> None:
    pdfs = sorted(p for f in FOLDERS for p in (DOCS / f).glob("*.pdf"))
    seg = DeterministicClauseSegmenter()
    rows = []
    for i, path in enumerate(pdfs, 1):
        doc = _parse_cached(path)
        nodes = clause_tree(doc)
        result = seg.segment(doc)
        issues = validate_tree(nodes, doc)
        arts = sum(1 for n in nodes if n.depth == 0 and n.marker_family == "article")
        regions = sum(1 for u in result.clauses if u.role is ClauseRole.REGION)
        secs = sum(1 for u in result.clauses if u.role is ClauseRole.SECTION)
        rows.append({
            "name": path.stem, "pages": doc.page_count, "clauses": len(result.clauses),
            "articles": arts, "sections": secs, "regions": regions,
            "max_depth": max((n.depth for n in nodes), default=-1),
            "invalid": len(issues), "trust": result.confidence.score,
            "review": result.confidence.needs_review,
            "reasons": result.confidence.reasons,
        })
        print(f"[{i}/{len(pdfs)}] parsed {path.name}", flush=True)

    print(f"\n{'trust':>5} {'rev':>4} {'pg':>4} {'cl':>4} {'art':>3} {'sec':>4} "
          f"{'reg':>3} {'d':>2} {'inv':>3}  document")
    for r in sorted(rows, key=lambda r: r["trust"]):
        flag = "ESC" if r["review"] else " ok"
        print(f"{r['trust']:5.2f} {flag:>4} {r['pages']:4} {r['clauses']:4} "
              f"{r['articles']:3} {r['sections']:4} {r['regions']:3} {r['max_depth']:2} "
              f"{r['invalid']:3}  {r['name'][:46]}")

    n = len(rows)
    empty = sum(1 for r in rows if r["clauses"] == 0)
    invalid = sum(1 for r in rows if r["invalid"] > 0)
    escalated = sum(1 for r in rows if r["review"])
    print(f"\n==== {n} held-out contracts ====")
    print(f"empty (0 clauses) : {empty}")
    print(f"invalid tree      : {invalid}   (structural-invariant failures)")
    print(f"gate escalates    : {escalated}/{n}")
    print("NOTE: gold-free — this checks structural health + whether the router "
          "fires, not section-level accuracy (no gold for these types).")


if __name__ == "__main__":
    main()
