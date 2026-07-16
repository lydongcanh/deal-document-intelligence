"""Evaluation harness for stage-5 clause classification, plus baselines.

Multi-label metrics:
  - micro P/R/F1 over all labels (incl. OTHER)
  - macro-F1 over the 41 deal types (excl. OTHER) — the Ansarada metric
  - per-type P/R/F1

It scores any predictor mapping clause text → set[ClauseType], so the same
harness measures the baseline today and the trained model later, unchanged.

Run:  poetry run python training/clause_classification/evaluate.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Callable

from deal_document_intelligence.contracts import ClauseType

DATA = Path("data/clause_classification")
OTHER = ClauseType.UNKNOWN

Predictor = Callable[[str], set[ClauseType]]
Example = tuple[str, set[ClauseType]]


def load_split(split: str = "test") -> list[Example]:
    examples: list[Example] = []
    for line in (DATA / f"{split}.jsonl").read_text().splitlines():
        if not line:
            continue
        row = json.loads(line)
        examples.append((row["text"], {ClauseType(x) for x in row["labels"]}))
    return examples


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def score(predictor: Predictor, examples: list[Example]) -> dict:
    tp, fp, fn, support = Counter(), Counter(), Counter(), Counter()
    for text, gold in examples:
        pred = predictor(text)
        for label in gold:
            support[label] += 1
        for label in pred | gold:
            if label in pred and label in gold:
                tp[label] += 1
            elif label in pred:
                fp[label] += 1
            else:
                fn[label] += 1
    labels = sorted(support, key=lambda t: t.value)
    per = {label: _prf(tp[label], fp[label], fn[label]) for label in labels}
    micro = _prf(sum(tp.values()), sum(fp.values()), sum(fn.values()))
    deal = [label for label in labels if label != OTHER]
    macro_deal_f1 = sum(per[label][2] for label in deal) / len(deal) if deal else 0.0
    return {"micro": micro, "macro_deal_f1": macro_deal_f1, "per": per, "support": support}


def report(name: str, res: dict) -> None:
    mp, mr, mf = res["micro"]
    print(f"\n=== {name} ===")
    print(f"micro    P={mp:.3f}  R={mr:.3f}  F1={mf:.3f}")
    print(f"macro-F1 (deal types, excl. OTHER): {res['macro_deal_f1']:.3f}")
    print(f"{'clause type':30} {'P':>5} {'R':>5} {'F1':>5} {'n':>6}")
    for label in sorted(res["per"], key=lambda t: -res["support"][t])[:12]:
        p, r, f = res["per"][label]
        print(f"{label.value:30} {p:5.2f} {r:5.2f} {f:5.2f} {res['support'][label]:6d}")


# --- baselines -------------------------------------------------------------
def all_other_baseline(text: str) -> set[ClauseType]:
    return {OTHER}


_KEYWORDS: dict[str, ClauseType] = {
    "governing law": ClauseType.GOVERNING_LAW,
    "insurance": ClauseType.INSURANCE,
    "audit": ClauseType.AUDIT_RIGHTS,
    "change of control": ClauseType.CHANGE_OF_CONTROL,
    "change in control": ClauseType.CHANGE_OF_CONTROL,
    "non-compete": ClauseType.NON_COMPETE,
    "not to compete": ClauseType.NON_COMPETE,
    "exclusiv": ClauseType.EXCLUSIVITY,
    "renew": ClauseType.RENEWAL_TERM,
    "effective date": ClauseType.EFFECTIVE_DATE,
    "expiration": ClauseType.EXPIRATION_DATE,
    "assign": ClauseType.ANTI_ASSIGNMENT,
    "license": ClauseType.LICENSE_GRANT,
    "warrant": ClauseType.WARRANTY_DURATION,
    "minimum": ClauseType.MINIMUM_COMMITMENT,
    "most favored": ClauseType.MOST_FAVORED_NATION,
    "solicit": ClauseType.NO_SOLICIT_OF_EMPLOYEES,
    "disparage": ClauseType.NON_DISPARAGEMENT,
    "escrow": ClauseType.SOURCE_CODE_ESCROW,
    "by and between": ClauseType.PARTIES,
    "for convenience": ClauseType.TERMINATION_FOR_CONVENIENCE,
}


def keyword_baseline(text: str) -> set[ClauseType]:
    low = text.lower()
    hits = {ctype for kw, ctype in _KEYWORDS.items() if kw in low}
    return hits or {OTHER}


if __name__ == "__main__":
    examples = load_split("test")
    print(f"test examples: {len(examples):,}")
    report("baseline: all-OTHER (floor)", score(all_other_baseline, examples))
    report("baseline: keyword", score(keyword_baseline, examples))
