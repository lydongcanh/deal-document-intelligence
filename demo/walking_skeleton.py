"""Phase 1 walking skeleton — one document flows through ALL stages end-to-end.

This is a *consumer* of `deal_document_intelligence`: it supplies a docling-based
Parser and rule/regex baselines for stages 4-7, wires them into the package's
`Pipeline`, and runs a real contract through it. The package itself depends on
none of this.

    poetry run python demo/walking_skeleton.py
"""

from __future__ import annotations

from pathlib import Path

from docling_parser import DoclingParser
from keyword_classifier import KeywordClassifier
from offset_linker import OffsetLinker
from regex_extractor import RegexExtractor
from rule_based_segmenter import RuleBasedSegmenter

from deal_document_intelligence.pipeline import Pipeline

HERE = Path(__file__).resolve().parent
REPO = HERE.parent


def main() -> None:
    source = HERE / "sample_contract.md"

    pipeline = Pipeline(
        parser=DoclingParser(),
        segmenter=RuleBasedSegmenter(),
        classifier=KeywordClassifier(),
        extractor=RegexExtractor(),
        linker=OffsetLinker(),
    )

    print(f"Running pipeline on {source.name} …\n")
    result = pipeline.run(source)

    doc = result.document
    print(f"=== DOCUMENT ===  {doc.doc_id}  ({doc.page_count} page(s), {len(doc.blocks)} blocks)\n")

    print(f"=== CLAUSES ({len(result.clauses)}) ===")
    for c in result.clauses:
        ctype = c.clause_type.value if c.clause_type else "?"
        conf = f"{c.classification_confidence:.2f}" if c.classification_confidence else "—"
        print(f"  [{c.number or '-':>3}] {ctype:<28} conf={conf}  «{(c.heading or c.text)[:40]}»")

    print(f"\n=== ENTITIES ({len(result.entities)}) ===")
    for e in result.entities:
        norm = f" → {e.normalized_value}" if e.normalized_value else ""
        print(f"  {e.type.value:<12} «{e.text}»{norm}  (clause {e.clause_id})")

    print(f"\n=== RELATIONS ({len(result.relations)}) ===  entity→clause links")

    failures = result.verify_evidence()
    print(f"\n=== EVIDENCE INTEGRITY ===  {'OK ✅' if not failures else f'{len(failures)} BROKEN ❌'}")

    out = REPO / "outputs" / f"{doc.doc_id}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(result.model_dump_json(indent=2))
    print(f"\nWrote evidence-backed JSON → {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
