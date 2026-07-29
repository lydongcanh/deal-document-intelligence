"""The normalised document every stage reads from (output of stages 1-2).

`text` is the single normalised string for the whole document; every downstream
fact points back into it by character offset. That is what makes results
evidence-backed. Everything here is produced by parsing, so `parse()` never
returns a half-filled document. Predicted properties such as language (see
`DetectedLanguage`) and document type are produced by later stages and live in
their own result objects, not on this one.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from deal_document_intelligence.contracts.block import Block
from deal_document_intelligence.contracts.evidence_span import EvidenceSpan


class ParsedDocument(BaseModel):
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
        """Check a span is in-bounds AND its stored `text` matches the source.

        Guards against offset drift and out-of-range spans — the key invariant
        for evidence integrity. A span whose `char_end` exceeds the document
        length fails here (Python slicing would otherwise silently truncate).
        """
        if not 0 <= span.char_start <= span.char_end <= len(self.text):
            return False
        return self.slice(span.char_start, span.char_end) == span.text
