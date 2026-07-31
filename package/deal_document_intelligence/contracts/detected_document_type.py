from __future__ import annotations

from pydantic import BaseModel, Field

from deal_document_intelligence.contracts.document_type import DocumentType


class DetectedDocumentType(BaseModel):
    """Output of the document-type stage.

    Deferred: no detector ships yet (see docs/03-document-type.md). This fixes a
    minimal contract, mirroring DetectedLanguage, so the future model has a defined
    shape to fill. The production result will likely grow (ranked top-k, an unknown
    probability, a review flag); that shape is recorded in docs/03 and added when we
    build the model.

    Kept separate from ParsedDocument so the parser's return type never carries a
    field it did not produce.
    """

    document_type: DocumentType | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
