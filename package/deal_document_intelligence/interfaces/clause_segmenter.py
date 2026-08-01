from __future__ import annotations

from typing import Protocol, runtime_checkable

from deal_document_intelligence.contracts import ParsedDocument, SegmentedClause


@runtime_checkable
class ClauseSegmenter(Protocol):
    """ClauseSegmenter interface — stage 4 (clause segmentation).

        Input : a ParsedDocument.
        Output: a list of SegmentedClause (structural: text, offsets, evidence, and the
            clause tree). Classification is a separate stage and contract.

    IMPLEMENTED in this package — contract-aware segmentation is a differentiator.
    Consumers may still supply their own by satisfying this Protocol.
    """

    def segment(self, document: ParsedDocument) -> list[SegmentedClause]: ...
