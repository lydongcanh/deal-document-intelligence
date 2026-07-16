"""The normalised document every stage reads from (output of stages 2-3).

`text` is the single normalised string for the whole document; every downstream
fact points back into it by character offset. That is what makes results
evidence-backed.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from deal_document_intelligence.contracts.block import Block
from deal_document_intelligence.contracts.evidence_span import EvidenceSpan


class CanonicalDocument(BaseModel):
    doc_id: str
    text: str
    blocks: list[Block] = Field(default_factory=list)
    source_path: str | None = None
    mime_type: str | None = None
    page_count: int | None = None
    meta: dict = Field(default_factory=dict)

    def slice(self, char_start: int, char_end: int) -> str:
        """Return the source substring for a char range."""
        return self.text[char_start:char_end]

    def verify(self, span: EvidenceSpan) -> bool:
        """Check a span's stored `text` still matches the canonical text.

        Guards against offset drift — the key invariant for evidence integrity.
        """
        return self.slice(span.char_start, span.char_end) == span.text
