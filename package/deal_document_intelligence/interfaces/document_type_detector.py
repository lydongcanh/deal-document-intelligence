"""DocumentTypeDetector interface — the document-type stage.

    Input : a ParsedDocument.
    Output: a DetectedDocumentType (the detected type with a confidence).

DEFERRED: no implementation ships yet. Unlike language ID, there is no
ready-made labelled dataset for deal document types, so a production detector is
a data-engineering and ML program, not a library wrap. See
docs/03-document-type.md for the rationale and the plan to revisit. This
interface fixes the seam so the future model has a defined slot to plug into.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from deal_document_intelligence.contracts import DetectedDocumentType, ParsedDocument


@runtime_checkable
class DocumentTypeDetector(Protocol):
    def detect(self, document: ParsedDocument) -> DetectedDocumentType: ...
