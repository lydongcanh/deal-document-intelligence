"""EntityExtractor interface — stage 6.

    Input : a ParsedDocument + its (classified) clauses.
    Output: a list of Entity (with evidence; normalisation happens at stage 8).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from deal_document_intelligence.contracts import ParsedDocument, SegmentedClause, Entity


@runtime_checkable
class EntityExtractor(Protocol):
    def extract(
        self, document: ParsedDocument, clauses: list[SegmentedClause]
    ) -> list[Entity]: ...
