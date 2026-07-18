"""Score the trained clause classifier on the TEST split — same shared metric as
the baselines (see metrics.py), so numbers are directly comparable.

Run:  poetry run python training/clause_classification/evaluate_model.py
"""

from __future__ import annotations

import json
from pathlib import Path

import torch
from metrics import OTHER, report, score
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from deal_document_intelligence.contracts import ClauseType

MODEL_DIR = Path("artifacts/models/clause_classifier")
DATA = Path("artifacts/data/clause_classification")


def main() -> None:
    threshold = json.loads((MODEL_DIR / "threshold.json").read_text())["threshold"]
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
    device = (
        "cuda" if torch.cuda.is_available()
        else "mps" if torch.backends.mps.is_available() else "cpu"
    )
    model.to(device).eval()

    id2label = model.config.id2label
    labels_by_idx = [
        ClauseType(id2label[i] if i in id2label else id2label[str(i)])
        for i in range(model.config.num_labels)
    ]

    texts, gold = [], []
    for line in (DATA / "test.jsonl").read_text().splitlines():
        if not line:
            continue
        row = json.loads(line)
        texts.append(row["text"])
        gold.append({ClauseType(x) for x in row["labels"]})

    pred: list[set[ClauseType]] = []
    with torch.no_grad():
        for i in range(0, len(texts), 32):
            enc = tokenizer(texts[i:i + 32], truncation=True, max_length=256,
                            padding=True, return_tensors="pt").to(device)
            probs = torch.sigmoid(model(**enc).logits).cpu().tolist()
            for row in probs:
                hit = {labels_by_idx[j] for j, p in enumerate(row) if p > threshold}
                pred.append(hit or {OTHER})

    report(f"TRAINED MODEL (threshold={threshold})", score(gold, pred))


if __name__ == "__main__":
    main()
