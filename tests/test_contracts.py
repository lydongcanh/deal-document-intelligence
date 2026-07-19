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
from deal_document_intelligence.pipeline import IntegrityError, Pipeline

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
            return [ClauseUnit(
                id="c1", text=document.text, char_start=0, char_end=len(document.text),
                evidence=[EvidenceSpan(page=1, char_start=0,
                                       char_end=len(document.text), text=document.text)],
            )]

    class FakeClassifier:
        def classify(self, clauses, document):
            for c in clauses:
                c.clause_type = ClauseType.GOVERNING_LAW
            return clauses

    class FakeEntityExtractor:
        def extract(self, document, clauses) -> list[Entity]:
            start = SAMPLE.index("Delaware")
            return [Entity(
                id="e1", type=EntityType.JURISDICTION, text="Delaware",
                evidence=[EvidenceSpan(page=1, char_start=start,
                                       char_end=start + len("Delaware"), text="Delaware")],
            )]

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
    assert result.validate_integrity() == []  # fully sound: evidence present, refs resolve
    assert result.meta["validation_issues"] == []  # pipeline surfaced the check (warn mode)

    class FakeAggregator:
        def aggregate(self, documents) -> DealIntelligence:
            return DealIntelligence(deal_id="d1", documents=documents)

    deal = DealPipeline(pipe, FakeAggregator()).run([Path("a.md"), Path("b.md")])
    assert deal.deal_id == "d1"
    assert len(deal.documents) == 2


def _codes(result: EvidenceBackedResult) -> set[str]:
    return {issue.code for issue in result.validate_integrity()}


def test_validate_flags_missing_evidence() -> None:
    result = EvidenceBackedResult(
        doc_id="doc-1", document=_doc(),
        entities=[Entity(id="e1", type=EntityType.OTHER, text="x")],  # no evidence
    )
    assert "missing_evidence" in _codes(result)


def test_validate_flags_dangling_relation() -> None:
    rel = Relation(id="r1", type=RelationType.ENTITY_IN_CLAUSE,
                   source_id="ghost", target_id="also-ghost")
    result = EvidenceBackedResult(doc_id="doc-1", document=_doc(), relations=[rel])
    assert "dangling_ref" in _codes(result)


def test_validate_flags_out_of_bounds_span() -> None:
    bad = EvidenceSpan(page=1, char_start=0, char_end=len(SAMPLE) + 50, text=SAMPLE)
    ent = Entity(id="e1", type=EntityType.OTHER, text=SAMPLE, evidence=[bad])
    result = EvidenceBackedResult(doc_id="doc-1", document=_doc(), entities=[ent])
    assert result.verify_evidence()  # out-of-bounds span caught, not silently truncated
    assert "span_mismatch" in _codes(result)


def test_validate_flags_doc_id_mismatch() -> None:
    result = EvidenceBackedResult(doc_id="WRONG", document=_doc())
    assert "doc_id_mismatch" in _codes(result)


def test_taxonomy_partition_is_complete_and_disjoint() -> None:
    from deal_document_intelligence.contracts import METADATA_TYPES, PROVISION_TYPES
    deal = {c for c in ClauseType if c != ClauseType.UNKNOWN}
    assert PROVISION_TYPES | METADATA_TYPES == deal          # covers all 41
    assert not (PROVISION_TYPES & METADATA_TYPES)             # no overlap
    assert ClauseType.UNKNOWN not in (PROVISION_TYPES | METADATA_TYPES)


def test_validate_flags_dangling_clause_id() -> None:
    doc = _doc()
    ent = Entity(id="e1", type=EntityType.OTHER, text="Delaware", clause_id="nope",
                 evidence=[EvidenceSpan(page=1, char_start=SAMPLE.index("Delaware"),
                                        char_end=SAMPLE.index("Delaware") + 8, text="Delaware")])
    result = EvidenceBackedResult(doc_id="doc-1", document=doc, entities=[ent])
    assert "dangling_clause_id" in _codes(result)


def test_strict_pipeline_raises_on_invalid_result() -> None:
    doc = _doc()

    class FakeParser:
        def parse(self, source: Path) -> CanonicalDocument:
            return doc

    class FakeLang:
        def detect(self, d: CanonicalDocument) -> CanonicalDocument:
            return d

    class FakeSeg:
        def segment(self, d: CanonicalDocument) -> list[ClauseUnit]:
            return []

    class FakeClf:
        def classify(self, clauses, d):
            return clauses

    class FakeEnt:
        def extract(self, d, clauses) -> list[Entity]:
            return [Entity(id="e1", type=EntityType.OTHER, text="x")]  # no evidence → invalid

    class FakeRel:
        def extract(self, d, clauses, entities) -> RelationExtraction:
            return RelationExtraction()

    class FakeRes:
        def resolve(self, d, entities) -> list[Entity]:
            return entities

    pipe = Pipeline(FakeParser(), FakeLang(), FakeSeg(), FakeClf(), FakeEnt(),
                    FakeRel(), FakeRes(), validation="strict")
    try:
        pipe.run(Path("x.md"))
        raise AssertionError("expected IntegrityError")
    except IntegrityError as e:
        assert e.issues


if __name__ == "__main__":
    test_evidence_integrity_holds()
    test_evidence_drift_is_caught()
    test_pipeline_and_deal_wiring_with_fakes()
    test_validate_flags_missing_evidence()
    test_validate_flags_dangling_relation()
    test_validate_flags_out_of_bounds_span()
    test_validate_flags_doc_id_mismatch()
    test_validate_flags_dangling_clause_id()
    test_taxonomy_partition_is_complete_and_disjoint()
    test_strict_pipeline_raises_on_invalid_result()
    print("All smoke tests passed ✅")
