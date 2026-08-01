"""ClauseClassifier interface — stage 5 (clause classification).

    Input : the clauses to classify + their ParsedDocument (for context).
    Output: one ClauseClassification per clause (keyed by clause id), so the
            segmentation output is left untouched and each stage's contract is
            fully populated on its own.

IMPLEMENTED in this package — a fine-tuned model (CUAD) is a differentiator.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from deal_document_intelligence.contracts import (
    ClauseClassification,
    SegmentedClause,
    ParsedDocument,
)


@runtime_checkable
class ClauseClassifier(Protocol):
    def classify(
        self, clauses: list[SegmentedClause], document: ParsedDocument
    ) -> list[ClauseClassification]: ...
