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
from deal_document_intelligence.contracts.clause_type import ClauseType
from deal_document_intelligence.contracts.clause_unit import ClauseUnit
from deal_document_intelligence.contracts.entity import Entity
from deal_document_intelligence.contracts.event import Event
from deal_document_intelligence.contracts.evidence_span import EvidenceSpan
from deal_document_intelligence.contracts.obligation import Obligation
from deal_document_intelligence.contracts.relation import Relation
from deal_document_intelligence.contracts.validation_issue import ValidationIssue


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
        catch missing evidence or dangling references — use `validate_integrity()`
        for the full check.
        """
        return [s for s in self.all_evidence() if not self.document.verify(s)]

    def validate_integrity(self) -> list[ValidationIssue]:
        """Full integrity check. Returns typed issues ([] = valid).

        Checks: doc_id consistency; unique ids; every content fact carries
        evidence; evidence spans verify (bounds + text) and reference valid
        pages/blocks; clause char-spans are in range and their text matches the
        document slice; the primary clause_type agrees with the top prediction;
        entity/obligation/event `clause_id` and relation source/target ids all
        resolve. Relations are links, so they are exempt from required-evidence.
        """
        doc = self.document
        n = len(doc.text)
        block_ids = {b.id for b in doc.blocks}
        clause_ids = {c.id for c in self.clauses}
        issues: list[ValidationIssue] = []

        def add(code: str, message: str, ref: str | None = None) -> None:
            issues.append(ValidationIssue(code=code, message=message, ref=ref))

        if self.doc_id != doc.doc_id:
            add("doc_id_mismatch", f"result {self.doc_id!r} != document {doc.doc_id!r}")

        facts = (("clause", self.clauses), ("entity", self.entities),
                 ("obligation", self.obligations), ("event", self.events))
        all_items = (*facts, ("relation", self.relations))

        seen: set[str] = set()
        known_ids: set[str] = set()
        for kind, items in all_items:
            for item in items:
                if item.id in seen:
                    add("duplicate_id", f"{kind} id {item.id!r} is not unique", item.id)
                seen.add(item.id)
                known_ids.add(item.id)

        for kind, items in facts:
            for item in items:
                if not item.evidence:
                    add("missing_evidence", f"{kind} {item.id!r} has no evidence", item.id)
                for span in item.evidence:
                    if not doc.verify(span):
                        add("span_mismatch",
                            f"{kind} {item.id!r} evidence [{span.char_start}:{span.char_end}] "
                            "is out-of-bounds or mismatched", item.id)
                    if doc.page_count and span.page > doc.page_count:
                        add("page_out_of_range",
                            f"{kind} {item.id!r} evidence page {span.page} > {doc.page_count}", item.id)
                    if span.block_id is not None and block_ids and span.block_id not in block_ids:
                        add("bad_block_id",
                            f"{kind} {item.id!r} evidence block_id {span.block_id!r} unknown", item.id)

        for clause in self.clauses:
            if not 0 <= clause.char_start <= clause.char_end <= n:
                add("clause_span_oob", f"clause {clause.id!r} char-span out of bounds", clause.id)
            elif doc.slice(clause.char_start, clause.char_end) != clause.text:
                add("clause_text_mismatch", f"clause {clause.id!r} text != document slice", clause.id)
            deal_preds = [p for p in clause.predictions if p.clause_type != ClauseType.UNKNOWN]
            if deal_preds and clause.clause_type not in (None, ClauseType.UNKNOWN):
                top = max(deal_preds, key=lambda p: p.score).clause_type
                if clause.clause_type != top:
                    add("primary_type_disagree",
                        f"clause {clause.id!r} primary {clause.clause_type.value} "
                        f"!= top prediction {top.value}", clause.id)

        for kind, items in facts[1:]:  # entity, obligation, event
            for item in items:
                cid = getattr(item, "clause_id", None)
                if cid is not None and cid not in clause_ids:
                    add("dangling_clause_id", f"{kind} {item.id!r} clause_id {cid!r} unknown", item.id)

        for relation in self.relations:
            for ref in (relation.source_id, relation.target_id):
                if ref not in known_ids:
                    add("dangling_ref", f"relation {relation.id!r} references unknown id {ref!r}", relation.id)

        return issues
