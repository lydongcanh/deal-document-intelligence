"""Baseline DealAggregator (stage 9b) — cross-document entity resolution by the
normalised alias key the resolver attached. Groups per-document entities that
share a key into one `CanonicalEntity` with mentions across all documents.

A minimal stand-in for real entity resolution (blocking + similarity + a model);
enough to show the deal-level product taking shape. Satisfies the
`DealAggregator` interface.
"""

from __future__ import annotations

from deal_document_intelligence.contracts import (
    CanonicalEntity,
    DealIntelligence,
    EntityMention,
    EvidenceBackedResult,
)


class NaiveDealAggregator:
    def __init__(self, deal_id: str = "demo-deal") -> None:
        self.deal_id = deal_id

    def aggregate(
        self, documents: list[EvidenceBackedResult]
    ) -> DealIntelligence:
        groups: dict[str, list[tuple[str, object]]] = {}
        for result in documents:
            for entity in result.entities:
                key = entity.meta.get("alias_key") or f"{entity.type.value}:{entity.text.lower()}"
                groups.setdefault(key, []).append((result.doc_id, entity))

        canonical: list[CanonicalEntity] = []
        for i, (key, members) in enumerate(groups.items()):
            texts = [e.text for _, e in members]
            canonical.append(CanonicalEntity(
                id=f"ce{i}",
                type=members[0][1].type,
                canonical_name=max(texts, key=len),
                aliases=sorted(set(texts)),
                mentions=[
                    EntityMention(
                        doc_id=doc_id, entity_id=e.id, text=e.text, evidence=e.evidence
                    )
                    for doc_id, e in members
                ],
                normalized_value=next(
                    (e.normalized_value for _, e in members if e.normalized_value), None
                ),
            ))

        return DealIntelligence(
            deal_id=self.deal_id,
            documents=documents,
            canonical_entities=canonical,
        )
