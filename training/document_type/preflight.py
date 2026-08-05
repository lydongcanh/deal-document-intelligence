"""Dataset preflight: FAIL before training unless the dataset is clean.

Run after building the dataset and before any baseline/transformer fit. It enforces
the integrity rules individual rows cannot check, and writes an immutable manifest so
the exact dataset used is recorded by hash. `baseline.py` refuses to train unless this
manifest exists and its per-file hashes match the input files.

Checks:
  - split-file match (every row's `split` equals the file it is in) and unique ids;
  - stored `text_sha256` matches `text`;
  - duplicates: no exact OR near-duplicate document ANYWHERE (within a split, e.g.
    template collapse in train, or across pools, e.g. contamination);
  - grouping: no org / document-family / source-document / template value spans pools;
  - class support: every EXPECTED label present in `train`, above a minimum;
  - readiness: every real row is human-verified.

Modes:
  - production (default): expected labels = all 24; fail-closed on any missing.
  - smoke: pass `--expected-labels a,b,c,other` to validate a disposable subset.

Run:  poetry run python training/document_type/preflight.py --data-dir <dir>
      ... --expected-labels nda,commercial_agreement,constitutional,other   # smoke

Note: duplicate detection is O(n^2) char-shingle Jaccard, pilot-only. Swap in
MinHash/LSH before large-scale runs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from example import DocTypeExample, Origin, Split
from labels import MODEL_LABELS
from preprocessing import sha256

_GROUP_KEYS = ("org_id", "document_family_id", "source_document_sha256", "template_cluster_id")


def _shingles(text: str, n: int = 5) -> set[str]:
    norm = " ".join(text.lower().split())
    return {norm[i:i + n] for i in range(len(norm) - n + 1)} or {norm}


def _jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if (a or b) else 1.0


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dataset_identity(all_rows: list[DocTypeExample]) -> str:
    """Canonical hash of the WHOLE dataset: every field of every row (label, split,
    provenance, review status, grouping), order-independent. Changing any of them
    changes the hash, unlike hashing text alone."""
    canon = sorted(json.dumps(r.model_dump(mode="json"), sort_keys=True) for r in all_rows)
    return sha256("\n".join(canon))


def load_all(data_dir: Path) -> dict[str, list[DocTypeExample]]:
    out: dict[str, list[DocTypeExample]] = {}
    for split in (s.value for s in Split):
        path = data_dir / f"{split}.jsonl"
        if not path.exists():
            continue
        rows = [DocTypeExample.model_validate_json(ln) for ln in path.read_text().splitlines() if ln.strip()]
        for r in rows:
            if r.split.value != split:
                raise ValueError(f"{path.name}: row {r.id} declares split {r.split.value}")
        out[split] = rows
    return out


def check(rows_by_split: dict[str, list[DocTypeExample]], expected_labels: list[str],
          min_support: int, near_dup: float) -> list[str]:
    errors: list[str] = []
    all_rows = [r for rows in rows_by_split.values() for r in rows]

    dup_ids = [i for i, c in Counter(r.id for r in all_rows).items() if c > 1]
    if dup_ids:
        errors.append(f"duplicate ids: {dup_ids}")

    for r in all_rows:
        if r.text_sha256 != sha256(r.text):
            errors.append(f"row {r.id}: text_sha256 mismatch")
        if r.origin is Origin.REAL and not r.eval_ready():
            errors.append(f"real row {r.id} not human-verified")

    errors += _duplicates(all_rows, near_dup)
    errors += _grouping(rows_by_split)

    train_counts = Counter(r.type for r in rows_by_split.get(Split.TRAIN.value, []))
    for label in expected_labels:
        n = train_counts.get(label, 0)
        if n == 0:
            errors.append(f"expected class {label!r} has no training examples")
        elif n < min_support:
            errors.append(f"expected class {label!r} has {n} training examples (< {min_support})")
    return errors


def _duplicates(all_rows: list[DocTypeExample], near_dup: float) -> list[str]:
    """Exact + near duplicates ANYWHERE (within a split or across pools)."""
    errors: list[str] = []
    by_hash: dict[str, list[DocTypeExample]] = defaultdict(list)
    for r in all_rows:
        by_hash[r.text_sha256].append(r)
    for group in by_hash.values():
        if len(group) > 1:
            where = [f"{r.split.value}:{r.id}" for r in group]
            errors.append(f"exact duplicate text: {where}")
    shingled = [(r, _shingles(r.text)) for r in all_rows]
    for (ra, sa), (rb, sb) in combinations(shingled, 2):
        if ra.text_sha256 == rb.text_sha256:
            continue  # already reported as exact
        if _jaccard(sa, sb) >= near_dup:
            errors.append(f"near-duplicate {ra.split.value}:{ra.id} ~ {rb.split.value}:{rb.id}")
    return errors


def _grouping(rows_by_split: dict[str, list[DocTypeExample]]) -> list[str]:
    errors: list[str] = []
    for key in _GROUP_KEYS:
        seen: dict[str, str] = {}  # value -> split
        for split, rows in rows_by_split.items():
            for r in rows:
                raw = getattr(r, key)
                if raw is None:
                    continue
                val = str(raw)
                if val in seen and seen[val] != split:
                    errors.append(f"{key}={val!r} spans pools {seen[val]} and {split}")
                seen[val] = split
    return errors


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--expected-labels", default="",
                    help="CSV subset for a smoke run; empty = all 24 (production, fail-closed)")
    ap.add_argument("--min-support", type=int, default=20)
    ap.add_argument("--near-dup", type=float, default=0.9)
    args = ap.parse_args()

    expected = [s.strip() for s in args.expected_labels.split(",") if s.strip()] or MODEL_LABELS
    unknown = [c for c in expected if c not in MODEL_LABELS]
    if unknown:
        raise SystemExit(f"--expected-labels contains non-labels: {unknown}")
    mode = "production" if set(expected) == set(MODEL_LABELS) else "smoke"

    rows_by_split = load_all(args.data_dir)
    errors = check(rows_by_split, expected, args.min_support, args.near_dup)
    if errors:
        print(f"PREFLIGHT FAILED ({mode}, {len(errors)} issues):")
        for e in errors:
            print(f"  - {e}")
        raise SystemExit(1)

    all_rows = [r for rows in rows_by_split.values() for r in rows]
    manifest = {
        "mode": mode,
        "dataset_hash": dataset_identity(all_rows),
        "per_file_sha256": {f"{s}.jsonl": _file_sha256(args.data_dir / f"{s}.jsonl") for s in rows_by_split},
        "counts": {s: len(rows) for s, rows in rows_by_split.items()},
        "train_class_counts": dict(Counter(r.type for r in rows_by_split.get(Split.TRAIN.value, []))),
        "expected_labels": expected,
        "labels": MODEL_LABELS,
        "near_dup_threshold": args.near_dup,
        "min_support": args.min_support,
    }
    (args.data_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"PREFLIGHT OK ({mode}). dataset_hash={manifest['dataset_hash'][:16]}  manifest written.")


if __name__ == "__main__":
    main()
