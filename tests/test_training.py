"""ML-workflow tests: the shared metric and the dataset dedup.

These guard the two regressions the reviews found — a diverged/crashing metric
and unchecked split leakage. `training/` isn't an installed package, so we add it
to the path; the dedup test needs the training deps (`datasets`) and skips if
they're absent.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "training" / "clause_classification"))

from metrics import DEAL_TYPES, OTHER, score  # noqa: E402

from deal_document_intelligence.contracts import ClauseType  # noqa: E402


def test_metric_is_41_labels_and_excludes_other_from_micro() -> None:
    gov = ClauseType.GOVERNING_LAW
    gold = [{gov}, {OTHER}]
    pred = [{gov}, {gov}]  # 2nd: OTHER gold, predicted gov → a deal false-positive
    res = score(gold, pred)
    # micro over deal types (OTHER excluded): tp=1, fp=1, fn=0 → F1 = 0.667
    assert round(res["micro"][2], 3) == 0.667
    # macro is averaged over ALL 41 deal types (the 40 unseen ones count as 0)
    assert len(DEAL_TYPES) == 41
    assert abs(res["macro_deal_f1"] - 0.6667 / 41) < 1e-3


def test_dedup_merges_labels_and_keeps_one_split() -> None:
    pytest.importorskip("datasets")
    from build_clause_dataset import ClauseDatasetBuilder
    from clause_example import ClauseExample

    a = ClauseExample(text="same text", labels=[ClauseType.GOVERNING_LAW],
                      source="cuad", doc_id="c1", split="train")
    b = ClauseExample(text="same text", labels=[ClauseType.INSURANCE],
                      source="cuad", doc_id="c2", split="test")
    kept = ClauseDatasetBuilder._dedup_across_splits([a, b])
    assert len(kept) == 1
    assert kept[0].split == "train"  # train > val > test priority
    assert set(kept[0].labels) == {ClauseType.GOVERNING_LAW, ClauseType.INSURANCE}  # merged
