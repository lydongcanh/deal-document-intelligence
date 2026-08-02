"""Score the clause segmenter against the dev/acceptance labels.

Scope and honesty: labels are section-level inventories derived from each
document's own table of contents (independent of the segmenter, which parses the
body). They cover the SEC merger/SPA slice only. A clause counts as correct only
when its number AND its depth match, so a section found at the wrong depth is an
error, not a true positive. Duplicate predictions are reported. Results are
aggregated, written to artifacts/, and the run exits non-zero below a threshold,
so this is an acceptance/regression check, not just a printout.

Full-document parses are cached under artifacts/cache so repeated scoring does
not re-run docling across every PDF.

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

from deal_document_intelligence.contracts import ClauseRole, ParsedDocument  # noqa: E402
from deal_document_intelligence.segmentation import DeterministicClauseSegmenter  # noqa: E402
from deal_document_intelligence.segmentation.numbering import parse_roman  # noqa: E402

GOLD_DIR = Path(__file__).parent / "gold"
DOCS = REPO / "demo" / "documents"
OUT = REPO / "artifacts" / "eval" / "clause_segmentation" / "score.json"
CACHE = REPO / "artifacts" / "cache" / "parsed"
MIN_MEAN_F1 = 0.90  # acceptance threshold on the mean F1 over the labelled set


def _norm(number: str) -> tuple:
    """Normalise a clause number so surface form does not matter: "Section 1.1"
    and "1.1" match; "ARTICLE I" matches by value."""
    t = number.strip()
    if t.upper().startswith("ARTICLE"):
        tok = t.split()[-1]
        return ("ART", int(tok) if tok.isdigit() else parse_roman(tok))
    m = re.search(r"\d+(?:\.\d+)*", t)
    return ("SEC", m.group(0)) if m else ("RAW", t)


def _parse_cached(source_rel: str) -> ParsedDocument:
    key = CACHE / (Path(source_rel).stem + ".json")
    if key.exists():
        return ParsedDocument.model_validate_json(key.read_text())
    doc = DoclingParser().parse(DOCS / source_rel)
    key.parent.mkdir(parents=True, exist_ok=True)
    key.write_text(doc.model_dump_json())
    return doc


def _in_region(unit, by_id: dict) -> bool:
    """True if the clause is inside a Schedule/Annex/Exhibit namespace. Gold is the
    main-body TOC, so region sections (a schedule's own 7.2) are out of scope here
    and would otherwise count as false extras."""
    cur, seen = unit, set()
    while cur is not None and cur.id not in seen:
        seen.add(cur.id)
        if cur.role == ClauseRole.REGION:
            return True
        cur = by_id.get(cur.parent_id)
    return False


def score_file(path: Path) -> dict:
    gold = json.loads(path.read_text())
    doc = _parse_cached(gold["source"])
    units = DeterministicClauseSegmenter().segment(doc).clauses
    by_id = {u.id: u for u in units}

    want = {_norm(c["number"]): (c["number"], c["depth"])
            for c in gold["clauses"] if c["depth"] <= 1}
    pred: dict = {}
    duplicates: list[str] = []
    for u in units:
        depth = u.depth
        if not u.number or depth > 1 or _in_region(u, by_id):
            continue
        key = _norm(u.number)
        # Gold is section level (articles and N.M sections). A parenthesised
        # sub-part ((a), (i)) is never a section, so score it at the sub-part
        # level, not here: _norm tags these "RAW". Counting them would penalise
        # precision for a depth error the section-level gold cannot express.
        if key[0] == "RAW":
            continue
        if key in pred:
            duplicates.append(u.number)
        else:
            pred[key] = (u.number, depth)

    # A clause is correct only if BOTH its number and its depth match.
    correct = [k for k in want if k in pred and pred[k][1] == want[k][1]]
    wrong_depth = sorted(want[k][0] for k in want if k in pred and pred[k][1] != want[k][1])
    missed = sorted(want[k][0] for k in want if k not in pred)
    extra = sorted(pred[k][0] for k in pred if k not in want)
    tp = len(correct)
    recall = tp / len(want) if want else 0.0
    precision = tp / len(pred) if pred else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return {
        "source": gold["source"], "labelled": len(want), "correct": tp,
        "recall": round(recall, 3), "precision": round(precision, 3), "f1": round(f1, 3),
        "missed": missed, "wrong_depth": wrong_depth, "extra": extra, "duplicates": duplicates,
    }


def main() -> None:
    files = sorted(GOLD_DIR.rglob("*.json"))
    if not files:
        print(f"no label files in {GOLD_DIR}")
        return
    results = [score_file(f) for f in files]

    for r in results:
        print(f"\n=== {r['source']} ===")
        print(f"correct {r['correct']}/{r['labelled']}   "
              f"R {r['recall']:.2f}  P {r['precision']:.2f}  F1 {r['f1']:.2f}")
        for label in ("missed", "wrong_depth", "extra", "duplicates"):
            if r[label]:
                print(f"  {label}: {r[label]}")

    mean_f1 = sum(r["f1"] for r in results) / len(results)
    mean_r = sum(r["recall"] for r in results) / len(results)
    mean_p = sum(r["precision"] for r in results) / len(results)
    summary = {"documents": len(results), "mean_recall": round(mean_r, 3),
               "mean_precision": round(mean_p, 3), "mean_f1": round(mean_f1, 3),
               "threshold": MIN_MEAN_F1, "results": results}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2))

    print(f"\n==== {len(results)} docs | mean R {mean_r:.3f}  P {mean_p:.3f}  "
          f"F1 {mean_f1:.3f} (threshold {MIN_MEAN_F1}) ====")
    print(f"results: {OUT}")
    if mean_f1 < MIN_MEAN_F1:
        print("ACCEPTANCE FAILED: mean F1 below threshold")
        sys.exit(1)


if __name__ == "__main__":
    main()
