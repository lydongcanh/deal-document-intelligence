"""One mention of a canonical entity in a specific document.

Deal-level entity resolution (stage 9b) groups per-document `Entity` objects
that refer to the same real-world thing into a `CanonicalEntity`; each grouped
occurrence is recorded as an `EntityMention` (which document, which entity, and
its evidence).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from deal_document_intelligence.contracts.evidence_span import EvidenceSpan


class EntityMention(BaseModel):
    doc_id: str
    entity_id: str
    text: str
    evidence: list[EvidenceSpan] = Field(default_factory=list)
