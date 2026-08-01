"""EntityResolver interface — stage 8.

    Input : a ParsedDocument + its extracted entities.
    Output: the entities with `normalized_value` filled and within-document
            aliases resolved (grouped via meta / normalized_value).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from deal_document_intelligence.contracts import ParsedDocument, Entity


@runtime_checkable
class EntityResolver(Protocol):
    def resolve(
        self, document: ParsedDocument, entities: list[Entity]
    ) -> list[Entity]: ...
