"""The pipeline's final output contract (stage 8).

Bundles every extracted layer together with the `CanonicalDocument` they
reference, so consumers can resolve any offset back to source text.
`verify_evidence()` enforces the core invariant: every stored evidence span
still matches the canonical text it points at.
"""

from __future__ import annotations

from collections.abc import Iterator

from pydantic import BaseModel, Field

from deal_document_intelligence.contracts.canonical_document import CanonicalDocument
from deal_document_intelligence.contracts.clause_unit import ClauseUnit
from deal_document_intelligence.contracts.entity import Entity
from deal_document_intelligence.contracts.event import Event
from deal_document_intelligence.contracts.evidence_span import EvidenceSpan
from deal_document_intelligence.contracts.obligation import Obligation
from deal_document_intelligence.contracts.relation import Relation


class EvidenceBackedResult(BaseModel):
    """Structured, traceable intelligence for one document."""

    doc_id: str
    document: CanonicalDocument
    clauses: list[ClauseUnit] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    obligations: list[Obligation] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    pipeline_version: str = "0.1.0"
    meta: dict = Field(default_factory=dict)

    def all_evidence(self) -> Iterator[EvidenceSpan]:
        """Every evidence span across every layer."""
        for clause in self.clauses:
            yield from clause.evidence
        for item in (*self.entities, *self.obligations, *self.events, *self.relations):
            yield from item.evidence

    def verify_evidence(self) -> list[EvidenceSpan]:
        """Return spans whose stored text no longer matches the document.

        An empty list means evidence integrity holds; a non-empty list means
        offsets have drifted and results can't be trusted.
        """
        return [s for s in self.all_evidence() if not self.document.verify(s)]
