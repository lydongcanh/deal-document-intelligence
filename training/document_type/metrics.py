"""Metrics for the document-type pilot: macro / weighted / per-class F1 with
confidence intervals, top-k accuracy, and a majority-class floor.

Two rules keep the numbers honest and stable:
  1. Every F1 uses the SAME explicit `labels` set. A metric that infers its label set
     from whatever happened to be predicted is unstable (a rare class dropping out
     changes the score). The caller declares the evaluation label set once.
  2. The bootstrap is class-STRATIFIED: it resamples within each true-class group, so a
     rare class never vanishes from a resample and the CI reflects real uncertainty.

Small real eval sets give wide intervals, so we report CIs and check pre-registered
thresholds against the interval, not a single point estimate.
"""

from __future__ import annotations

from collections import Counter

import numpy as np
from sklearn.metrics import f1_score

_SEED = 20260805  # fixed so CIs are reproducible


def majority_floor(
    train_labels: list[str], eval_labels: list[str], labels: list[str]
) -> float:
    """Macro-F1 of always predicting the most frequent training label.

    Deterministic tie-break: the alphabetically smallest label among the most frequent.
    """
    counts = Counter(train_labels)
    top = max(counts.values())
    most_common = min(c for c, n in counts.items() if n == top)
    preds = [most_common] * len(eval_labels)
    return float(
        f1_score(eval_labels, preds, labels=labels, average="macro", zero_division=0)
    )


def score(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict:
    """Point estimates, all computed over the SAME explicit `labels`."""
    per = np.asarray(
        f1_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
    )
    return {
        "macro_f1": float(
            f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)
        ),
        "weighted_f1": float(
            f1_score(y_true, y_pred, labels=labels, average="weighted", zero_division=0)
        ),
        "per_class_f1": {lbl: float(v) for lbl, v in zip(labels, per)},
    }


def _ci(values: np.ndarray, alpha: float) -> tuple[float, float]:
    lo, hi = np.quantile(values, [alpha / 2, 1 - alpha / 2])
    return float(lo), float(hi)


def bootstrap(
    y_true: list[str],
    y_pred: list[str],
    labels: list[str],
    n: int = 1000,
    alpha: float = 0.05,
) -> dict:
    """Class-stratified percentile bootstrap for macro-F1 and per-class F1."""
    rng = np.random.default_rng(_SEED)
    yt, yp = np.asarray(y_true), np.asarray(y_pred)
    # Build groups in EXPLICIT `labels` order (not set(y_true)): a set's iteration order
    # varies with Python's per-process string hash seed, which made the RNG consume in a
    # different order each process and produced non-reproducible CIs.
    groups = [g for c in labels if len(g := np.flatnonzero(yt == c))]
    macro = np.empty(n)
    per = {lbl: np.empty(n) for lbl in labels}
    for i in range(n):
        idx = np.concatenate([rng.choice(g, size=len(g), replace=True) for g in groups])
        macro[i] = float(
            f1_score(yt[idx], yp[idx], labels=labels, average="macro", zero_division=0)
        )
        pc = np.asarray(
            f1_score(yt[idx], yp[idx], labels=labels, average=None, zero_division=0)
        )
        for lbl, v in zip(labels, pc):
            per[lbl][i] = float(v)
    return {
        "macro_f1_ci": _ci(macro, alpha),
        "per_class_f1_ci": {lbl: _ci(per[lbl], alpha) for lbl in labels},
    }


def top_k_accuracy(
    y_true: list[str], proba: np.ndarray, model_classes: list[str], k: int = 3
) -> float:
    """Fraction of documents whose true label is in the model's top-k predictions."""
    order = np.argsort(proba, axis=1)[:, ::-1][:, :k]
    arr = np.asarray(model_classes)
    return float(np.mean([yt in arr[row] for yt, row in zip(y_true, order)]))


def report(name: str, y_true: list[str], y_pred: list[str], labels: list[str]) -> dict:
    """Print and return the full metric block for one evaluation over `labels`."""
    s = score(y_true, y_pred, labels)
    ci = bootstrap(y_true, y_pred, labels)
    m_lo, m_hi = ci["macro_f1_ci"]
    print(f"\n== {name} ==  (labels: {', '.join(labels)})")
    print(f"macro-F1    {s['macro_f1']:.3f}   (95% CI {m_lo:.3f}-{m_hi:.3f})")
    print(f"weighted-F1 {s['weighted_f1']:.3f}")
    for lbl in labels:
        lo, hi = ci["per_class_f1_ci"][lbl]
        print(f"  {lbl:24} F1 {s['per_class_f1'][lbl]:.3f}  (CI {lo:.3f}-{hi:.3f})")
    return {**s, **ci}
