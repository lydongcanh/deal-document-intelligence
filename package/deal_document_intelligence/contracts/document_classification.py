"""Document-level classification — output of stage 3 (detect language + type).

Deliberately kept separate from `CanonicalDocument`. Parsing produces the
document; a later stage predicts these fields. Composing them side by side (see
`EvidenceBackedResult`) rather than folding them into the document means no
method ever returns a document with these fields silently empty. Because this is
a prediction, it can carry optional confidences.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from deal_document_intelligence.contracts.document_type import DocumentType


class DocumentClassification(BaseModel):
    language: str | None = Field(default=None, description="ISO 639-1, e.g. 'en'")
    language_confidence: float | None = Field(default=None, ge=0, le=1)
    document_type: DocumentType | None = None
    document_type_confidence: float | None = Field(default=None, ge=0, le=1)
