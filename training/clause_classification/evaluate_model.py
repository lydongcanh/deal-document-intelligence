"""Score the trained clause classifier on the TEST split (component eval).

Predicts via `TransformerClauseClassifier` — the *same* code the pipeline uses —
so thresholding (including per-label thresholds from tune_thresholds.py) is
applied exactly as in production. One source of truth, no divergence. Metrics are
the shared `metrics.score` (over the 41 deal types; OTHER excluded from micro).

Run:  poetry run python training/clause_classification/evaluate_model.py
"""

from __future__ import annotations

import json
from pathlib import Path

from metrics import OTHER, report, score

from deal_document_intelligence.classification.transformer_clause_classifier import (
    TransformerClauseClassifier,
)
from deal_document_intelligence.contracts import ParsedDocument, ClauseType, SegmentedClause

MODEL_DIR = Path("artifacts/models/clause_classifier")
DATA = Path("artifacts/data/clause_classification")


def main() -> None:
    clf = TransformerClauseClassifier(MODEL_DIR)  # picks up per-label thresholds if present

    texts, gold = [], []
    for line in (DATA / "test.jsonl").read_text().splitlines():
        if not line:
            continue
        row = json.loads(line)
        texts.append(row["text"])
        gold.append({ClauseType(x) for x in row["labels"]})

    # Wrap each test row as a one-clause document and run the real classifier.
    clauses = [
        SegmentedClause(id=str(i), text=text, char_start=0, char_end=len(text))
        for i, text in enumerate(texts)
    ]
    clf.classify(clauses, ParsedDocument(doc_id="test", text=""))

    pred: list[set[ClauseType]] = []
    for clause in clauses:
        hits = {p.clause_type for p in clause.predictions if p.clause_type != OTHER}
        pred.append(hits or {OTHER})

    kind = "per-label" if clf.label_thresholds else f"global {clf.threshold}"
    report(f"TRAINED MODEL (thresholds: {kind})", score(gold, pred))


if __name__ == "__main__":
    main()
