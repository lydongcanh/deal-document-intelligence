"""Shared scoring for clause classification — ONE metric definition for every
path (baseline eval, trained-model eval, and — via the same rules — training).

Centralising this is deliberate: the evaluators previously duplicated the metric
code and drifted (one crashed, one averaged 40 labels instead of 41). Import
from here so they cannot diverge again.

Definitions:
  - micro-F1 over the **41 deal types only** (OTHER excluded, so the abundant,
    easy OTHER class can't inflate the headline number)
  - macro-F1 over the **fixed 41 deal types** (labels absent from a split count
    as F1 0, so the metric never silently shrinks)
  - per-type P/R/F1 for the labels present in the gold set
"""

from __future__ import annotations

from collections import Counter

from deal_document_intelligence.contracts import ClauseType

OTHER = ClauseType.UNKNOWN
DEAL_TYPES = [c for c in ClauseType if c != OTHER]  # the fixed 41


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def score(
    gold: list[set[ClauseType]], pred: list[set[ClauseType]]
) -> dict:
    tp, fp, fn, support = Counter(), Counter(), Counter(), Counter()
    for g, p in zip(gold, pred):
        for label in g:
            support[label] += 1
        for label in p | g:
            if label in p and label in g:
                tp[label] += 1
            elif label in p:
                fp[label] += 1
            else:
                fn[label] += 1

    micro = prf(
        sum(tp[t] for t in DEAL_TYPES),
        sum(fp[t] for t in DEAL_TYPES),
        sum(fn[t] for t in DEAL_TYPES),
    )
    macro_deal_f1 = sum(prf(tp[t], fp[t], fn[t])[2] for t in DEAL_TYPES) / len(DEAL_TYPES)
    per = {label: prf(tp[label], fp[label], fn[label]) for label in support}
    return {"micro": micro, "macro_deal_f1": macro_deal_f1, "per": per, "support": support}


def report(name: str, res: dict) -> None:
    mp, mr, mf = res["micro"]
    print(f"\n=== {name} ===")
    print(f"micro    P={mp:.3f} R={mr:.3f} F1={mf:.3f}  (over the 41 deal types, OTHER excluded)")
    print(f"macro-F1 (all {len(DEAL_TYPES)} deal types): {res['macro_deal_f1']:.3f}")
    print(f"{'clause type':30} {'P':>5} {'R':>5} {'F1':>5} {'n':>6}")
    ranked = sorted((c for c in res["per"] if c != OTHER),
                    key=lambda t: -res["support"][t])
    for label in ranked[:12]:
        p, r, f = res["per"][label]
        print(f"{label.value:30} {p:5.2f} {r:5.2f} {f:5.2f} {res['support'][label]:6d}")
