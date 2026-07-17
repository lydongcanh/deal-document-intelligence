"""A segmented clause, optionally classified into a type.

Produced by stage 4 (segmentation) with `clause_type=None`; stage 5
(classification) fills in `clause_type` and `classification_confidence`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from deal_document_intelligence.contracts.clause_type import ClauseType
from deal_document_intelligence.contracts.evidence_span import EvidenceSpan


class ClauseUnit(BaseModel):
    id: str
    text: str
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    number: str | None = Field(default=None, description="clause number, e.g. '5.1'")
    heading: str | None = None
    clause_type: ClauseType | None = None
    classification_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    model_version: str | None = Field(default=None, description="model/version that classified it")
    meta: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_span(self) -> ClauseUnit:
        if self.char_end < self.char_start:
            raise ValueError(f"char_end {self.char_end} < char_start {self.char_start}")
        return self
