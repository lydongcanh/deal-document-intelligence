"""Phase-0 smoke tests: the data contracts validate, evidence integrity is
enforced, and the pipeline orchestrator composes stages via the Protocols.

Runnable with pytest, or directly:
    poetry run python tests/test_contracts.py
"""

from __future__ import annotations

from pathlib import Path

from deal_document_intelligence.contracts import (
    Block,
    BlockType,
    CanonicalDocument,
    ClauseType,
    ClauseUnit,
    Entity,
    EntityType,
    EvidenceBackedResult,
    EvidenceSpan,
    Extractions,
    Relation,
    RelationType,
)
from deal_document_intelligence.pipeline import Pipeline

SAMPLE = "This Agreement is governed by the laws of the State of Delaware."


def _doc() -> CanonicalDocument:
    return CanonicalDocument(
        doc_id="doc-1",
        text=SAMPLE,
        blocks=[
            Block(
                id="b1",
                type=BlockType.PARAGRAPH,
                text=SAMPLE,
                page=1,
                char_start=0,
                char_end=len(SAMPLE),
            )
        ],
        page_count=1,
    )


def test_evidence_integrity_holds() -> None:
    doc = _doc()
    start = SAMPLE.index("Delaware")
    span = EvidenceSpan(
        page=1, char_start=start, char_end=start + len("Delaware"),
        text="Delaware", block_id="b1",
    )
    entity = Entity(
        id="e1", type=EntityType.JURISDICTION, text="Delaware",
        normalized_value="US-DE", evidence=[span], clause_id="c1",
    )
    clause = ClauseUnit(
        id="c1", text=SAMPLE, char_start=0, char_end=len(SAMPLE),
        clause_type=ClauseType.GOVERNING_LAW, classification_confidence=0.9,
        evidence=[EvidenceSpan(page=1, char_start=0, char_end=len(SAMPLE), text=SAMPLE)],
    )
    result = EvidenceBackedResult(
        doc_id="doc-1", document=doc, clauses=[clause], entities=[entity]
    )
    assert result.verify_evidence() == []  # every span matches the source text


def test_evidence_drift_is_caught() -> None:
    doc = _doc()
    bad = EvidenceSpan(page=1, char_start=0, char_end=4, text="XXXX")  # wrong text
    entity = Entity(id="e1", type=EntityType.OTHER, text="XXXX", evidence=[bad])
    result = EvidenceBackedResult(doc_id="doc-1", document=doc, entities=[entity])
    assert len(result.verify_evidence()) == 1  # drift detected


def test_pipeline_wiring_with_fakes() -> None:
    """The orchestrator composes stages purely via the Protocols (duck-typed)."""
    doc = _doc()

    class FakeParser:
        def parse(self, source: Path) -> CanonicalDocument:
            return doc

    class FakeSegmenter:
        def segment(self, document: CanonicalDocument) -> list[ClauseUnit]:
            return [ClauseUnit(id="c1", text=document.text, char_start=0,
                               char_end=len(document.text))]

    class FakeClassifier:
        def classify(self, clauses, document):
            for c in clauses:
                c.clause_type = ClauseType.GOVERNING_LAW
            return clauses

    class FakeExtractor:
        def extract(self, document, clauses) -> Extractions:
            return Extractions(
                entities=[Entity(id="e1", type=EntityType.JURISDICTION, text="Delaware")]
            )

    class FakeLinker:
        def link(self, document, clauses, extractions) -> list[Relation]:
            return [Relation(id="r1", type=RelationType.ENTITY_IN_CLAUSE,
                             source_id="e1", target_id="c1")]

    pipe = Pipeline(
        FakeParser(), FakeSegmenter(), FakeClassifier(), FakeExtractor(), FakeLinker()
    )
    result = pipe.run(Path("dummy.pdf"))
    assert result.doc_id == "doc-1"
    assert result.clauses[0].clause_type == ClauseType.GOVERNING_LAW
    assert result.entities[0].text == "Delaware"
    assert result.relations[0].source_id == "e1"
    assert result.verify_evidence() == []


if __name__ == "__main__":
    test_evidence_integrity_holds()
    test_evidence_drift_is_caught()
    test_pipeline_wiring_with_fakes()
    print("All Phase-0 smoke tests passed ✅")
