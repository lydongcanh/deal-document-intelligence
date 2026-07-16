"""A span of text denoting a real-world entity, optionally normalised."""

from __future__ import annotations

from pydantic import BaseModel, Field

from deal_document_intelligence.contracts.entity_type import EntityType
from deal_document_intelligence.contracts.evidence_span import EvidenceSpan


class Entity(BaseModel):
    id: str
    type: EntityType
    text: str
    normalized_value: str | None = Field(
        default=None, description="e.g. '2020-01-01', 'USD 1000000', 'P30D'"
    )
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    clause_id: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    meta: dict = Field(default_factory=dict)
