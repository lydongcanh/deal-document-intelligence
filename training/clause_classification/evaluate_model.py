"""Score the trained clause classifier on the TEST split — apples-to-apples with
the 0.166 baseline floor (which was measured on test).

Loads models/clause_classifier + its tuned threshold, batch-predicts on test,
and reports micro-F1, macro-F1 over deal types, and the top per-type F1s.

Run:  poetry run python training/clause_classification/evaluate_model.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from deal_document_intelligence.contracts import ClauseType

MODEL_DIR = Path("artifacts/models/clause_classifier")
DATA = Path("artifacts/data/clause_classification")
OTHER = ClauseType.UNKNOWN
DEAL_TYPES = [c for c in ClauseType if c != OTHER]  # fixed 41 — same metric everywhere


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def main() -> None:
    threshold = json.loads((MODEL_DIR / "threshold.json").read_text())["threshold"]
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model.to(device).eval()

    id2label = model.config.id2label
    n = model.config.num_labels
    labels_by_idx = [
        ClauseType(id2label[i] if i in id2label else id2label[str(i)]) for i in range(n)
    ]

    texts, gold = [], []
    for line in (DATA / "test.jsonl").read_text().splitlines():
        if not line:
            continue
        row = json.loads(line)
        texts.append(row["text"])
        gold.append({ClauseType(x) for x in row["labels"]})

    preds: list[set[ClauseType]] = []
    with torch.no_grad():
        for i in range(0, len(texts), 32):
            enc = tokenizer(texts[i:i + 32], truncation=True, max_length=256,
                            padding=True, return_tensors="pt").to(device)
            probs = torch.sigmoid(model(**enc).logits).cpu().tolist()
            for row in probs:
                hit = {labels_by_idx[j] for j, p in enumerate(row) if p > threshold}
                preds.append(hit or {OTHER})

    tp, fp, fn, support = Counter(), Counter(), Counter(), Counter()
    for g, p in zip(gold, preds):
        for label in g:
            support[label] += 1
        for label in p | g:
            if label in p and label in g:
                tp[label] += 1
            elif label in p:
                fp[label] += 1
            else:
                fn[label] += 1

    micro = _prf(sum(tp.values()), sum(fp.values()), sum(fn.values()))
    per = {label: _prf(tp[label], fp[label], fn[label]) for label in support}
    macro = sum(_prf(tp[t], fp[t], fn[t])[2] for t in DEAL_TYPES) / len(DEAL_TYPES)

    print(f"=== TEST (threshold={threshold}) ===")
    print(f"micro F1       : {micro[2]:.3f}")
    print(f"macro-deal F1  : {macro:.3f}   (over all {len(DEAL_TYPES)} deal types)")
    print(f"{'clause type':30} {'P':>5} {'R':>5} {'F1':>5} {'n':>5}")
    for label in sorted(deal, key=lambda x: -support[x])[:12]:
        p, r, f = per[label]
        print(f"{label.value:30} {p:5.2f} {r:5.2f} {f:5.2f} {support[label]:5d}")


if __name__ == "__main__":
    main()
