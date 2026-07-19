"""Tune a PER-LABEL decision threshold on the validation split — no retraining.

The model outputs an independent probability per clause type. Turning a
probability into yes/no needs a cutoff. One global cutoff (0.10) is a blunt
compromise: trigger-happy types over-fire while rare types under-fire. Here each
type picks the cutoff that maximises *its* F1 on the **validation** set (never
test — that stays the untouched final grade). A type with too few val positives
(< MIN_SUPPORT) can't be tuned reliably, so it falls back to the global cutoff.

The label space is read from the model itself, so this works whether the model
has 41 outputs (OTHER derived) or a legacy 42.

Output: artifacts/models/clause_classifier/thresholds.json  {clause_type: cutoff}

    make clause-tune-thresholds
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import f1_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from deal_document_intelligence.contracts import ClauseType

MODEL_DIR = Path("artifacts/models/clause_classifier")
DATA = Path("artifacts/data/clause_classification")
OTHER = ClauseType.UNKNOWN
MIN_SUPPORT = 20
GRID = [round(0.05 * k, 2) for k in range(1, 19)]  # 0.05 … 0.90


def _model_labels(model) -> list[ClauseType]:
    id2label = model.config.id2label
    return [
        ClauseType(id2label[i] if i in id2label else id2label[str(i)])
        for i in range(model.config.num_labels)
    ]


def main() -> None:
    tpath = MODEL_DIR / "threshold.json"
    global_t = json.loads(tpath.read_text())["threshold"] if tpath.exists() else 0.5

    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
    device = (
        "cuda" if torch.cuda.is_available()
        else "mps" if torch.backends.mps.is_available() else "cpu"
    )
    model.to(device).eval()
    labels = _model_labels(model)
    l2i = {label: i for i, label in enumerate(labels)}

    texts, gold_rows = [], []
    for line in (DATA / "val.jsonl").read_text().splitlines():
        if not line:
            continue
        row = json.loads(line)
        texts.append(row["text"])
        vec = [0] * len(labels)
        for name in row["labels"]:
            ct = ClauseType(name)
            if ct in l2i:
                vec[l2i[ct]] = 1
        gold_rows.append(vec)
    gold = np.array(gold_rows)

    probs = []
    with torch.no_grad():
        for i in range(0, len(texts), 32):
            enc = tokenizer(texts[i:i + 32], truncation=True, max_length=256,
                            padding=True, return_tensors="pt").to(device)
            probs.append(torch.sigmoid(model(**enc).logits).cpu().numpy())
    P = np.concatenate(probs, axis=0)

    tunable = [label for label in labels if label != OTHER]
    thresholds: dict[str, float] = {}
    for label in tunable:
        j = l2i[label]
        support = int(gold[:, j].sum())
        if support < MIN_SUPPORT:
            thresholds[label.value] = global_t  # too few positives to trust a tuned cutoff
            continue
        best_t, best_f = global_t, -1.0
        for t in GRID:  # ascending grid; >= keeps the HIGHER cutoff on ties (favours precision)
            f = f1_score(gold[:, j], (P[:, j] > t).astype(int), zero_division=0)
            if f >= best_f:
                best_f, best_t = f, t
        thresholds[label.value] = best_t

    (MODEL_DIR / "thresholds.json").write_text(json.dumps(thresholds, indent=2))

    def macro(cutoff_of) -> float:
        return float(np.mean([
            f1_score(gold[:, l2i[label]], (P[:, l2i[label]] > cutoff_of(label)).astype(int),
                     zero_division=0)
            for label in tunable
        ]))

    before = macro(lambda label: global_t)
    after = macro(lambda label: thresholds[label.value])
    tuned = sum(1 for label in tunable if thresholds[label.value] != global_t)
    print(f"val macro-F1: global {global_t} = {before:.3f}  →  per-label = {after:.3f}")
    print(f"tuned {tuned}/{len(tunable)} labels (rest kept global {global_t}; MIN_SUPPORT={MIN_SUPPORT})")
    print(f"saved → {MODEL_DIR / 'thresholds.json'}")


if __name__ == "__main__":
    main()
