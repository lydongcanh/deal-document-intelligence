"""Baseline document-type classifier: TF-IDF + linear (Logistic Regression).

The number the published model must beat. Simple, fast, interpretable: for
document-type, distinctive vocabulary carries most of the signal.

Fail-closed guards:
  - refuses to run unless a preflight `manifest.json` exists AND the input files' hashes
    match it, so contamination/grouping checks cannot be skipped;
  - `--eval-labels` is a PREREGISTERED set; every one must be present in the eval pool
    with minimum support, so a class cannot silently drop out of macro-F1;
  - each loaded row's `split` must match its file; every eval row must be human-verified;
  - `real_test` is refused unless --allow-test is passed.
The evaluated pipeline + a run manifest (linked to the dataset hash) are saved so the
evaluated model is exactly what could later be published.

Run (smoke):
  poetry run python training/document_type/preflight.py --data-dir <dir> --expected-labels nda,commercial_agreement,constitutional,other
  poetry run python training/document_type/baseline.py  --data-dir <dir> --eval-labels nda,commercial_agreement,constitutional,other
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from example import DocTypeExample, Split
from labels import MODEL_LABELS
from metrics import majority_floor, report, top_k_accuracy
from preprocessing import MAX_TOKENS, document_opening


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_split(data_dir: Path, split: str) -> list[DocTypeExample]:
    """Load one split, asserting each row's declared split matches the filename."""
    path = data_dir / f"{split}.jsonl"
    rows = [DocTypeExample.model_validate_json(ln) for ln in path.read_text().splitlines() if ln.strip()]
    bad = [r.id for r in rows if r.split.value != split]
    if bad:
        raise ValueError(f"{path.name} contains rows whose split != {split}: {bad}")
    return rows


def verify_manifest(data_dir: Path, files: list[str]) -> dict:
    """Require a preflight manifest and that the input files match it by hash."""
    path = data_dir / "manifest.json"
    if not path.exists():
        raise SystemExit("no preflight manifest.json; run preflight.py first")
    manifest = json.loads(path.read_text())
    per_file = manifest.get("per_file_sha256", {})
    for f in files:
        name = f"{f}.jsonl"
        if per_file.get(name) != _file_sha256(data_dir / name):
            raise SystemExit(f"{name} changed since preflight (hash mismatch); re-run preflight.py")
    return manifest


def require_eval_support(rows: list[DocTypeExample], eval_labels: list[str], min_support: int) -> list[str]:
    """A preregistered eval class must not silently vanish from the metric."""
    counts = Counter(r.type for r in rows)
    return [f"eval label {c!r} has {counts.get(c, 0)} docs (< {min_support})"
            for c in eval_labels if counts.get(c, 0) < min_support]


def texts_labels(rows: list[DocTypeExample]) -> tuple[list[str], list[str]]:
    return [document_opening(r.text) for r in rows], [r.type for r in rows]


def top_features(pipe: Pipeline, k: int = 12) -> dict[str, list[str]]:
    """Top positive TF-IDF features per class, to catch synthetic/template shortcuts."""
    vec: TfidfVectorizer = pipe.named_steps["tfidf"]
    clf: LogisticRegression = pipe.named_steps["clf"]
    names = np.asarray(vec.get_feature_names_out())
    coef = clf.coef_
    rows = coef if coef.shape[0] == len(clf.classes_) else np.vstack([-coef[0], coef[0]])
    return {cls: names[np.argsort(row)[::-1][:k]].tolist() for cls, row in zip(clf.classes_, rows)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--eval-labels", required=True, help="preregistered CSV of pilot eval classes")
    ap.add_argument("--eval-split", default=Split.REAL_DEV.value)
    ap.add_argument("--min-eval-support", type=int, default=1)
    ap.add_argument("--out-dir", type=Path, default=Path("artifacts/models/doctype-baseline"))
    ap.add_argument("--allow-test", action="store_true",
                    help="required to evaluate on real_test (the single-use test set)")
    args = ap.parse_args()

    if args.eval_split == Split.REAL_TEST.value and not args.allow_test:
        raise SystemExit("real_test is the single-use test set; pass --allow-test to use it.")

    eval_labels = [s.strip() for s in args.eval_labels.split(",") if s.strip()]
    unknown = [c for c in eval_labels if c not in MODEL_LABELS]
    if unknown:
        raise SystemExit(f"--eval-labels contains non-labels: {unknown}")

    manifest = verify_manifest(args.data_dir, [Split.TRAIN.value, args.eval_split])
    train = load_split(args.data_dir, Split.TRAIN.value)
    ev = load_split(args.data_dir, args.eval_split)

    not_ready = [r.id for r in ev if not r.eval_ready()]
    if not_ready:
        raise SystemExit(f"eval rows not human-verified: {not_ready}")
    support_errors = require_eval_support(ev, eval_labels, args.min_eval_support)
    if support_errors:
        raise SystemExit("preregistered eval labels lack support:\n  " + "\n  ".join(support_errors))

    x_tr, y_tr = texts_labels(train)
    x_ev, y_ev = texts_labels(ev)
    print(f"train={len(x_tr)} synthetic | {args.eval_split}={len(x_ev)} real | "
          f"eval labels (preregistered): {', '.join(eval_labels)}")

    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(sublinear_tf=True, ngram_range=(1, 2),
                                  min_df=1, max_features=50000, strip_accents="unicode")),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
    ])
    pipe.fit(x_tr, y_tr)

    print(f"\nmajority-class floor macro-F1: {majority_floor(y_tr, y_ev, eval_labels):.3f}")
    preds = list(pipe.predict(x_ev))
    result = report(f"TF-IDF + LogReg (eval={args.eval_split})", y_ev, preds, eval_labels)
    proba = pipe.predict_proba(x_ev)
    top3 = top_k_accuracy(y_ev, proba, list(pipe.classes_), k=3)
    print(f"top-3 accuracy: {top3:.3f}")

    print("\ntop features per class (inspect for synthetic/template artifacts):")
    for cls, feats in top_features(pipe).items():
        print(f"  {cls:24} {', '.join(feats)}")

    _save(args, pipe, eval_labels, {**result, "top3": top3}, train, ev, manifest["dataset_hash"])


def _save(args, pipe: Pipeline, eval_labels: list[str], result: dict,
          train: list[DocTypeExample], ev: list[DocTypeExample], dataset_hash: str) -> None:
    """Persist the exact evaluated pipeline + a run manifest linked to the dataset hash."""
    args.out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, args.out_dir / "model.joblib")
    manifest = {
        "model": "tfidf+logreg-baseline",
        "dataset_hash": dataset_hash,
        "model_labels": MODEL_LABELS,
        "trained_classes": list(pipe.classes_),
        "eval_labels": eval_labels,
        "eval_split": args.eval_split,
        "preprocessing": {"document_opening_max_tokens": MAX_TOKENS},
        "versions": {"scikit_learn": sklearn.__version__, "numpy": np.__version__},
        "data": {"n_train": len(train), "n_eval": len(ev)},
        "result": result,
    }
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\nsaved model + manifest to {args.out_dir}")


if __name__ == "__main__":
    main()
