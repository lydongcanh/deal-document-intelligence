"""Phase 1 walking skeleton — the finalized pipeline, end-to-end.

A *consumer* of `deal_document_intelligence`: it supplies a docling parser and
rule/regex baselines for every stage, wires them into `Pipeline` (single doc)
and `DealPipeline` (whole data room), and runs two real contracts through them.
The package depends on none of this.

    poetry run python demo/walking_skeleton.py            # keyword baseline (stage 5)
    poetry run python demo/walking_skeleton.py --trained  # trained Legal-XLM-R classifier
"""

from __future__ import annotations

import argparse
from pathlib import Path

from baseline_relation_extractor import BaselineRelationExtractor
from docling_parser import DoclingParser
from keyword_classifier import KeywordClassifier
from naive_deal_aggregator import NaiveDealAggregator
from regex_entity_extractor import RegexEntityExtractor
from rule_based_segmenter import RuleBasedSegmenter
from simple_language_detector import SimpleLanguageDetector
from simple_resolver import SimpleResolver

from deal_document_intelligence.deal_pipeline import DealPipeline
from deal_document_intelligence.pipeline import Pipeline

HERE = Path(__file__).resolve().parent
REPO = HERE.parent


def build_pipeline(trained: bool) -> Pipeline:
    if trained:
        # the differentiator model, straight from the package (stage 5)
        from deal_document_intelligence.classification.transformer_clause_classifier import (
            TransformerClauseClassifier,
        )
        classifier = TransformerClauseClassifier()
    else:
        classifier = KeywordClassifier()
    return Pipeline(
        parser=DoclingParser(),
        language_detector=SimpleLanguageDetector(),
        segmenter=RuleBasedSegmenter(),
        classifier=classifier,
        entity_extractor=RegexEntityExtractor(),
        relation_extractor=BaselineRelationExtractor(),
        resolver=SimpleResolver(),
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trained", action="store_true",
                    help="use the trained Legal-XLM-R classifier instead of the keyword baseline")
    args = ap.parse_args()

    sources = [HERE / "sample_contract.md", HERE / "sample_amendment.md"]
    pipeline = build_pipeline(args.trained)

    # ---- document-level (stage 9a) on the first contract ----
    result = pipeline.run(sources[0])
    doc = result.document
    print(f"=== DOCUMENT: {doc.doc_id} ===  (stage-5 classifier: "
          f"{'trained Legal-XLM-R' if args.trained else 'keyword baseline'})")
    print(f"  language={doc.language}  type={doc.document_type.value if doc.document_type else '?'}"
          f"  pages={doc.page_count}  blocks={len(doc.blocks)}")
    print(f"  entities={len(result.entities)}  obligations={len(result.obligations)}"
          f"  events={len(result.events)}  relations={len(result.relations)}")
    print(f"  evidence integrity: {'OK ✅' if not result.verify_evidence() else 'BROKEN ❌'}")
    print(f"  clauses ({len(result.clauses)}) — classified type @ confidence:")
    for c in result.clauses:
        ctype = c.clause_type.value if c.clause_type else "?"
        conf = f"{c.classification_confidence:.2f}" if c.classification_confidence else "—"
        print(f"    [{c.number or '-':>2}] {ctype:<28} @{conf}  «{(c.heading or c.text)[:44]}»")

    # ---- deal-level (stage 9b) across BOTH documents ----
    deal = DealPipeline(pipeline, NaiveDealAggregator(deal_id="acme-globex")).run(sources)
    print(f"\n=== DEAL: {deal.deal_id} ===  {len(deal.documents)} documents")
    print(f"  canonical entities resolved across documents ({len(deal.canonical_entities)}):")
    for ce in deal.canonical_entities:
        docs = sorted({m.doc_id for m in ce.mentions})
        cross = "  ← spans multiple docs" if len(docs) > 1 else ""
        print(f"    {ce.type.value:<12} «{ce.canonical_name}»  seen in {docs}{cross}")

    out = REPO / "artifacts" / "outputs" / f"deal_{deal.deal_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(deal.model_dump_json(indent=2))
    print(f"\nWrote deal intelligence → {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
