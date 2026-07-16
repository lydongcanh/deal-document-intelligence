"""Classifier interface — stage 5 (clause classification).

    Input : the clauses to classify + their CanonicalDocument (for context).
    Output: the same clauses with `clause_type` and
            `classification_confidence` populated.

IMPLEMENTED in this package — a fine-tuned model (CUAD) is a differentiator.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from deal_document_intelligence.contracts import CanonicalDocument, ClauseUnit


@runtime_checkable
class Classifier(Protocol):
    def classify(
        self, clauses: list[ClauseUnit], document: CanonicalDocument
    ) -> list[ClauseUnit]: ...
