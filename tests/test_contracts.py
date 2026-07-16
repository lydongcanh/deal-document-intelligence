"""Smoke tests: the data contracts validate, evidence integrity is enforced, and
the Pipeline / DealPipeline compose stages via the Protocols (with fakes).

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
    DealIntelligence,
    Entity,
    EntityType,
    EvidenceBackedResult,
    EvidenceSpan,
    Relation,
    RelationExtraction,
    RelationType,
)
from deal_document_intelligence.deal_pipeline import DealPipeline
from deal_document_intelligence.pipeline import Pipeline

SAMPLE = "This Agreement is governed by the laws of the State of Delaware."


def _doc() -> CanonicalDocument:
    return CanonicalDocument(
        doc_id="doc-1",
        text=SAMPLE,
        blocks=[
            Block(id="b1", type=BlockType.PARAGRAPH, text=SAMPLE,
                  page=1, char_start=0, char_end=len(SAMPLE))
        ],
        page_count=1,
    )


def test_evidence_integrity_holds() -> None:
    doc = _doc()
    start = SAMPLE.index("Delaware")
    span = EvidenceSpan(page=1, char_start=start, char_end=start + len("Delaware"),
                        text="Delaware", block_id="b1")
    entity = Entity(id="e1", type=EntityType.JURISDICTION, text="Delaware",
                    normalized_value="US-DE", evidence=[span], clause_id="c1")
    clause = ClauseUnit(id="c1", text=SAMPLE, char_start=0, char_end=len(SAMPLE),
                        clause_type=ClauseType.GOVERNING_LAW, classification_confidence=0.9,
                        evidence=[EvidenceSpan(page=1, char_start=0, char_end=len(SAMPLE), text=SAMPLE)])
    result = EvidenceBackedResult(doc_id="doc-1", document=doc, clauses=[clause], entities=[entity])
    assert result.verify_evidence() == []


def test_evidence_drift_is_caught() -> None:
    doc = _doc()
    bad = EvidenceSpan(page=1, char_start=0, char_end=4, text="XXXX")  # wrong text
    entity = Entity(id="e1", type=EntityType.OTHER, text="XXXX", evidence=[bad])
    result = EvidenceBackedResult(doc_id="doc-1", document=doc, entities=[entity])
    assert len(result.verify_evidence()) == 1


def test_pipeline_and_deal_wiring_with_fakes() -> None:
    """Pipeline (9a) and DealPipeline (9b) compose stages purely via Protocols."""
    doc = _doc()

    class FakeParser:
        def parse(self, source: Path) -> CanonicalDocument:
            return doc

    class FakeLanguageDetector:
        def detect(self, document: CanonicalDocument) -> CanonicalDocument:
            document.language = "en"
            return document

    class FakeSegmenter:
        def segment(self, document: CanonicalDocument) -> list[ClauseUnit]:
            return [ClauseUnit(id="c1", text=document.text, char_start=0,
                               char_end=len(document.text))]

    class FakeClassifier:
        def classify(self, clauses, document):
            for c in clauses:
                c.clause_type = ClauseType.GOVERNING_LAW
            return clauses

    class FakeEntityExtractor:
        def extract(self, document, clauses) -> list[Entity]:
            return [Entity(id="e1", type=EntityType.JURISDICTION, text="Delaware")]

    class FakeRelationExtractor:
        def extract(self, document, clauses, entities) -> RelationExtraction:
            return RelationExtraction(relations=[
                Relation(id="r1", type=RelationType.ENTITY_IN_CLAUSE,
                         source_id="e1", target_id="c1")])

    class FakeResolver:
        def resolve(self, document, entities) -> list[Entity]:
            return entities

    pipe = Pipeline(FakeParser(), FakeLanguageDetector(), FakeSegmenter(),
                    FakeClassifier(), FakeEntityExtractor(), FakeRelationExtractor(),
                    FakeResolver())
    result = pipe.run(Path("dummy.md"))
    assert result.document.language == "en"
    assert result.clauses[0].clause_type == ClauseType.GOVERNING_LAW
    assert result.entities[0].text == "Delaware"
    assert result.relations[0].source_id == "e1"
    assert result.verify_evidence() == []

    class FakeAggregator:
        def aggregate(self, documents) -> DealIntelligence:
            return DealIntelligence(deal_id="d1", documents=documents)

    deal = DealPipeline(pipe, FakeAggregator()).run([Path("a.md"), Path("b.md")])
    assert deal.deal_id == "d1"
    assert len(deal.documents) == 2


if __name__ == "__main__":
    test_evidence_integrity_holds()
    test_evidence_drift_is_caught()
    test_pipeline_and_deal_wiring_with_fakes()
    print("All smoke tests passed ✅")
