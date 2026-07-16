"""A dated or triggerable occurrence (termination, renewal, change-of-control …)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from deal_document_intelligence.contracts.evidence_span import EvidenceSpan


class Event(BaseModel):
    id: str
    type: str
    text: str
    date: str | None = Field(default=None, description="normalised date, if any")
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    clause_id: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    meta: dict = Field(default_factory=dict)
