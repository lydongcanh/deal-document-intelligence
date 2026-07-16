"""A duty a party owes — the core of what deal review cares about."""

from __future__ import annotations

from pydantic import BaseModel, Field

from deal_document_intelligence.contracts.evidence_span import EvidenceSpan


class Obligation(BaseModel):
    id: str
    text: str
    obligor: str | None = Field(default=None, description="party/entity that owes it")
    obligee: str | None = Field(default=None, description="party/entity it is owed to")
    action: str | None = None
    condition: str | None = Field(default=None, description="trigger / precondition")
    due: str | None = Field(default=None, description="normalised deadline, if any")
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    clause_id: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    model_version: str | None = Field(default=None, description="model/version that produced this")
    meta: dict = Field(default_factory=dict)
