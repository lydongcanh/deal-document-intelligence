"""Deal-level intelligence (stage 9b) — the cross-document aggregate.

A data room is many documents. This bundles every per-document
`EvidenceBackedResult` together with the deal-wide canonical entity registry and
any cross-document relations. This is the deal-level product the pipeline builds
toward.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from deal_document_intelligence.contracts.canonical_entity import CanonicalEntity
from deal_document_intelligence.contracts.evidence_backed_result import (
    EvidenceBackedResult,
)
from deal_document_intelligence.contracts.relation import Relation


class DealIntelligence(BaseModel):
    deal_id: str
    documents: list[EvidenceBackedResult] = Field(default_factory=list)
    canonical_entities: list[CanonicalEntity] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)  # cross-document
    pipeline_version: str = "0.1.0"
    meta: dict = Field(default_factory=dict)
