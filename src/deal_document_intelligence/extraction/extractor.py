"""Extractor interface — stage 6 (entities + obligations/events).

    Input : a CanonicalDocument + its (classified) clauses.
    Output: an Extractions bundle (entities, obligations, events).

HYBRID: generic entities may come from a consumer-supplied NER baseline; the
deal-specific extraction (roles, obligations, events) is implemented here.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from deal_document_intelligence.contracts import (
    CanonicalDocument,
    ClauseUnit,
    Extractions,
)


@runtime_checkable
class Extractor(Protocol):
    def extract(
        self, document: CanonicalDocument, clauses: list[ClauseUnit]
    ) -> Extractions: ...
