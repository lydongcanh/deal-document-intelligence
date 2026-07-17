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
        """Return spans that are out-of-bounds or whose text no longer matches.

        An empty list means every *present* span is sound. Note this does NOT
        catch missing evidence or dangling references — use `validate()` for the
        full integrity check.
        """
        return [s for s in self.all_evidence() if not self.document.verify(s)]

    def validate(self) -> list[str]:
        """Full integrity check. Returns human-readable issues ([] = valid).

        Checks: doc_id consistency; every content fact (clause/entity/obligation/
        event) carries evidence; every evidence span verifies (bounds + text);
        clause char-spans are in range; and every relation references an id that
        actually exists. Relations are treated as links, so they are exempt from
        the required-evidence rule.
        """
        doc = self.document
        n = len(doc.text)
        issues: list[str] = []

        if self.doc_id != doc.doc_id:
            issues.append(f"doc_id mismatch: result {self.doc_id!r} != document {doc.doc_id!r}")

        known_ids: set[str] = set()
        content = (
            ("clause", self.clauses), ("entity", self.entities),
            ("obligation", self.obligations), ("event", self.events),
        )
        for kind, items in content:
            for item in items:
                known_ids.add(item.id)
                if not item.evidence:
                    issues.append(f"{kind} {item.id!r} has no evidence")
                for span in item.evidence:
                    if not doc.verify(span):
                        issues.append(
                            f"{kind} {item.id!r} evidence [{span.char_start}:{span.char_end}] "
                            "is out-of-bounds or does not match the source text"
                        )

        for clause in self.clauses:
            if not 0 <= clause.char_start <= clause.char_end <= n:
                issues.append(f"clause {clause.id!r} char-span out of bounds")

        for relation in self.relations:
            for ref in (relation.source_id, relation.target_id):
                if ref not in known_ids:
                    issues.append(f"relation {relation.id!r} references unknown id {ref!r}")

        return issues
