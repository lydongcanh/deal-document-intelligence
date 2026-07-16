"""A typed link between two extracted items, identified by their ids."""

from __future__ import annotations

from pydantic import BaseModel, Field

from deal_document_intelligence.contracts.evidence_span import EvidenceSpan
from deal_document_intelligence.contracts.relation_type import RelationType


class Relation(BaseModel):
    id: str
    type: RelationType
    source_id: str
    target_id: str
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    model_version: str | None = Field(default=None, description="model/version that produced this")
    meta: dict = Field(default_factory=dict)
