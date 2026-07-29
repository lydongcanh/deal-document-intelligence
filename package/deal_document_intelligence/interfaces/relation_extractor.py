"""RelationExtractor interface — stage 7.

    Input : a CanonicalDocument, its clauses, and the extracted entities.
    Output: a RelationExtraction (obligations, events, relations).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from deal_document_intelligence.contracts import (
    CanonicalDocument,
    ClauseUnit,
    Entity,
    RelationExtraction,
)


@runtime_checkable
class RelationExtractor(Protocol):
    def extract(
        self,
        document: CanonicalDocument,
        clauses: list[ClauseUnit],
        entities: list[Entity],
    ) -> RelationExtraction: ...
