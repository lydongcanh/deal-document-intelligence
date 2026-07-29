"""DealAggregator interface — stage 9b.

    Input : the per-document EvidenceBackedResult for every document in a deal.
    Output: DealIntelligence — the documents plus a deal-wide canonical-entity
            registry (cross-document resolution) and any cross-document relations.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from deal_document_intelligence.contracts import DealIntelligence, EvidenceBackedResult


@runtime_checkable
class DealAggregator(Protocol):
    def aggregate(
        self, documents: list[EvidenceBackedResult]
    ) -> DealIntelligence: ...
