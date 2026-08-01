"""Measure the deterministic clause segmenter across a document corpus.

Phase 2 of segmentation (see docs/04). We have no gold labels yet, so this
measures what we can without them:

- parse success rate,
- validation pass rate against the invariants in validation.py
  (source-aligned, no overlap, child inside parent, monotonic, text
  conservation),
- coverage and anomaly signals: clauses per document, article count, max depth,
  zero-clause documents.

This finds where the deterministic core breaks. Exact-boundary and
document-perfect metrics need a hand-labelled gold set, which is a later step.

Usage:
    python eval/measure_segmentation.py [docs_dir] [--pages N]

Results are written to artifacts/eval/ (gitignored), not committed.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "demo"))  # reuse the demo's docling parser
from docling_parser import DoclingParser  # noqa: E402

from deal_document_intelligence.segmentation import (  # noqa: E402
    clause_tree,
    generate_candidates,
    validate_tree,
)

DEFAULT_DOCS = REPO / "demo" / "documents"
OUT = REPO / "artifacts" / "eval" / "clause_segmentation" / "measure.json"


def measure(docs_dir: Path, page_range: tuple[int, int] | None) -> list[dict]:
    pdfs = sorted(p for p in docs_dir.rglob("*") if p.suffix.lower() == ".pdf")
    print(f"documents: {len(pdfs)}  (pages={page_range or 'all'})", flush=True)

    parser = DoclingParser(page_range=page_range)  # models load once, reused
    results: list[dict] = []
    for i, path in enumerate(pdfs, 1):
        record: dict = {"file": str(path.relative_to(docs_dir))}
        try:
            doc = parser.parse(path)
            nodes = clause_tree(doc)
            issues = validate_tree(nodes, doc)
            starts = [c for c in generate_candidates(doc) if c.at_block_start]
            record.update(
                {
                    "ok": True,
                    "pages": doc.page_count,
                    "blocks": len(doc.blocks),
                    "block_start_candidates": len(starts),
                    "clauses": len(nodes),
                    "articles": sum(1 for n in nodes if n.depth == 0),
                    "max_depth": max((n.depth for n in nodes), default=-1),
                    "validation_issues": len(issues),
                    "issue_sample": issues[:5],
                    "body_start": nodes[0].marker_text if nodes else None,
                }
            )
        except (
            Exception
        ) as exc:  # record and continue; one bad doc must not stop the run
            record.update(
                {
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "trace": traceback.format_exc()[-400:],
                }
            )
        results.append(record)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(results, indent=2))
        print(
            f"[{i}/{len(pdfs)}] {record['file']}  ok={record['ok']}  "
            f"clauses={record.get('clauses')}  issues={record.get('validation_issues')}",
            flush=True,
        )
    return results


def _summary(results: list[dict]) -> None:
    ok = [r for r in results if r["ok"]]
    print("\n==== SUMMARY ====", flush=True)
    print(f"parsed ok        : {len(ok)}/{len(results)}", flush=True)
    print(f"zero-clause docs : {sum(1 for r in ok if r['clauses'] == 0)}", flush=True)
    print(
        f"docs w/ issues   : {sum(1 for r in ok if r['validation_issues'] > 0)}",
        flush=True,
    )
    if ok:
        print(
            f"avg clauses/doc  : {sum(r['clauses'] for r in ok) / len(ok):.0f}",
            flush=True,
        )
    print(f"results: {OUT}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("docs_dir", nargs="?", default=str(DEFAULT_DOCS))
    ap.add_argument(
        "--pages",
        type=int,
        default=None,
        help="parse only the first N pages of each document (default: all)",
    )
    args = ap.parse_args()
    page_range = (1, args.pages) if args.pages else None
    _summary(measure(Path(args.docs_dir), page_range))


if __name__ == "__main__":
    main()
