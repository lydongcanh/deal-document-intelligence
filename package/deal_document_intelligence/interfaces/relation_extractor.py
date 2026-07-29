"""RelationExtractor interface — stage 7.

    Input : a ParsedDocument, its clauses, and the extracted entities.
    Output: a RelationExtraction (obligations, events, relations).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from deal_document_intelligence.contracts import (
    ParsedDocument,
    ClauseUnit,
    Entity,
    RelationExtraction,
)


@runtime_checkable
class RelationExtractor(Protocol):
    def extract(
        self,
        document: ParsedDocument,
        clauses: list[ClauseUnit],
        entities: list[Entity],
    ) -> RelationExtraction: ...
