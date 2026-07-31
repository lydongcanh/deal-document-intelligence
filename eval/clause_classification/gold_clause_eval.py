"""Phase A — end-to-end gold evaluation of clause classification.

Runs the FULL pipeline (docling parse → segment → the trained classifier) on each
gold document and scores **document-level clause presence** against hand-labelled
gold. Crucially this scores the model on *predicted* clauses (what the segmenter
actually produces), not clean CUAD sentences — so it surfaces the train/inference
gap that isolated test-set F1 hides.

v1 gold set: short authored English contracts with authoritative document-level
labels. Next: real PDFs, plus gold clause boundaries + evidence (not just presence).

    make clause-gold-eval
    poetry run python eval/gold_clause_eval.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# NOTE: STALE. This imports walking-skeleton demo modules that were removed
# (rule_based_segmenter, regex_entity_extractor, ...). It needs rebuilding against
# the current interfaces before it runs. Paths below are already updated.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "demo"))  # reuse the demo's library baselines

from baseline_relation_extractor import BaselineRelationExtractor  # noqa: E402
from docling_parser import DoclingParser  # noqa: E402
from regex_entity_extractor import RegexEntityExtractor  # noqa: E402
from rule_based_segmenter import RuleBasedSegmenter  # noqa: E402
from simple_language_detector import SimpleLanguageDetector  # noqa: E402
from simple_resolver import SimpleResolver  # noqa: E402

from deal_document_intelligence.classification.transformer_clause_classifier import (  # noqa: E402
    TransformerClauseClassifier,
)
from deal_document_intelligence.contracts import (  # noqa: E402
    METADATA_TYPES,
    PROVISION_TYPES,
    ClauseType,
    EvidenceBackedResult,
)
from deal_document_intelligence.pipeline import Pipeline  # noqa: E402

GOLD_DIR = HERE / "gold"
CRITICAL = {
    ClauseType.GOVERNING_LAW, ClauseType.CHANGE_OF_CONTROL,
    ClauseType.TERMINATION_FOR_CONVENIENCE, ClauseType.CAP_ON_LIABILITY,
    ClauseType.ANTI_ASSIGNMENT,
}


def _build_pipeline() -> Pipeline:
    return Pipeline(
        parser=DoclingParser(),
        language_detector=SimpleLanguageDetector(),
        segmenter=RuleBasedSegmenter(),
        classifier=TransformerClauseClassifier(),  # the trained Legal-XLM-R model
        entity_extractor=RegexEntityExtractor(),
        relation_extractor=BaselineRelationExtractor(),
        resolver=SimpleResolver(),
        validation="warn",
    )


def _predicted_types(result: EvidenceBackedResult) -> set[ClauseType]:
    """Doc-level set of predicted deal types (union over all clauses' predictions)."""
    types: set[ClauseType] = set()
    for clause in result.clauses:
        for pred in clause.predictions:
            if pred.clause_type != ClauseType.UNKNOWN:
                types.add(pred.clause_type)
        if clause.clause_type and clause.clause_type != ClauseType.UNKNOWN:
            types.add(clause.clause_type)
    return types


def main() -> None:
    gold = {
        name: {ClauseType(v) for v in types}
        for name, types in json.loads((GOLD_DIR / "labels.json").read_text()).items()
    }
    pipeline = _build_pipeline()
    tp = fp = fn = crit_hit = crit_total = 0
    print(f"gold documents: {len(gold)}  (PROVISION presence on PREDICTED clauses, end-to-end)\n")

    for name, gold_types in gold.items():
        pred_all = _predicted_types(pipeline.run(GOLD_DIR / "docs" / f"{name}.md"))
        # Score PROVISIONS only — metadata types (title/parties/dates) are document
        # attributes, not provisions, so they don't belong in "clause presence".
        gold_p, pred_p = gold_types & PROVISION_TYPES, pred_all & PROVISION_TYPES
        hits, missed, spurious = gold_p & pred_p, gold_p - pred_p, pred_p - gold_p
        tp += len(hits)
        fn += len(missed)
        fp += len(spurious)
        crit_hit += len(gold_p & CRITICAL & pred_p)
        crit_total += len(gold_p & CRITICAL)
        print(f"--- {name} ---")
        print(f"  provision hits     : {sorted(t.value for t in hits)}")
        print(f"  provision MISSED   : {sorted(t.value for t in missed)}")
        print(f"  provision spurious : {sorted(t.value for t in spurious)}")
        print(f"  (metadata detected, reported separately: "
              f"{sorted(t.value for t in pred_all & METADATA_TYPES)})")

    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    print("\n=== DOCUMENT-LEVEL PROVISION PRESENCE (on predicted clauses) ===")
    print(f"precision {p:.3f}  recall {r:.3f}  F1 {f:.3f}   (tp={tp} fp={fp} fn={fn})")
    print(f"critical-clause recall: {crit_hit}/{crit_total}")


if __name__ == "__main__":
    main()
