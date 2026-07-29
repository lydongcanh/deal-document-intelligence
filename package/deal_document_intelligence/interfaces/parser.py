"""Parser interface — stages 1-3 (ingest → parse/OCR → structure).

    Input : a path to a source document (PDF/DOCX/scan/…).
    Output: a ParsedDocument (normalised text + blocks with page/char offsets).

DELIBERATELY NOT IMPLEMENTED in this package. Parsing/OCR/structure is a
commodity, and the choice of tool (docling, AWS Textract, Azure Document
Intelligence, unstructured, …) belongs to the consumer. The package only fixes
the contract: whatever you plug in must return a `ParsedDocument`. You can
self-check your adapter with `ParsedDocument.verify()` /
`EvidenceBackedResult.verify_evidence()`.

It's a `Protocol`, so no base class to inherit — any object with a matching
`parse` method satisfies it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from deal_document_intelligence.contracts import ParsedDocument


@runtime_checkable
class Parser(Protocol):
    def parse(self, source: Path) -> ParsedDocument: ...
