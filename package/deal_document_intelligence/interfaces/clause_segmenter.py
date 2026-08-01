from __future__ import annotations

from typing import Protocol, runtime_checkable

from deal_document_intelligence.contracts import ParsedDocument, SegmentationResult


@runtime_checkable
class ClauseSegmenter(Protocol):
    """ClauseSegmenter interface — stage 4 (clause segmentation).

        Input : a ParsedDocument.
        Output: a SegmentationResult: the SegmentedClause tree (structural: text,
            offsets, evidence, hierarchy) bundled with a confidence score so a
            caller can route a low-confidence document to review. Classification
            is a separate stage and contract.

    IMPLEMENTED in this package — contract-aware segmentation is a differentiator.
    Consumers may still supply their own by satisfying this Protocol.
    """

    def segment(self, document: ParsedDocument) -> SegmentationResult: ...
