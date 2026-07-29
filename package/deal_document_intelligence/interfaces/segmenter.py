"""Segmenter interface — stage 4 (clause segmentation).

    Input : a ParsedDocument.
    Output: a list of ClauseUnit (with offsets/evidence; clause_type left None).

IMPLEMENTED in this package — contract-aware segmentation is a differentiator.
Consumers may still supply their own by satisfying this Protocol.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from deal_document_intelligence.contracts import ParsedDocument, ClauseUnit


@runtime_checkable
class Segmenter(Protocol):
    def segment(self, document: ParsedDocument) -> list[ClauseUnit]: ...
