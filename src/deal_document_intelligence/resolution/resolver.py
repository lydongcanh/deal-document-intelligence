"""Resolver interface — stage 8.

    Input : a CanonicalDocument + its extracted entities.
    Output: the entities with `normalized_value` filled and within-document
            aliases resolved (grouped via meta / normalized_value).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from deal_document_intelligence.contracts import CanonicalDocument, Entity


@runtime_checkable
class Resolver(Protocol):
    def resolve(
        self, document: CanonicalDocument, entities: list[Entity]
    ) -> list[Entity]: ...
