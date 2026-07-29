"""A pointer back to the exact source text supporting a fact.

The `text` field is denormalised (a copy of the source substring) so a result is
human-readable on its own; `char_start:char_end` remains the authoritative
reference into `ParsedDocument.text`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from deal_document_intelligence.contracts.bbox import BBox


class EvidenceSpan(BaseModel):
    page: int = Field(ge=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    text: str
    block_id: str | None = None
    bbox: BBox | None = None

    @model_validator(mode="after")
    def _check_span(self) -> EvidenceSpan:
        if self.char_end < self.char_start:
            raise ValueError(f"char_end {self.char_end} < char_start {self.char_start}")
        return self
