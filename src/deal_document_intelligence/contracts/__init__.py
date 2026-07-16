"""Typed data contracts passed between pipeline stages — the backbone.

One class per module; this package re-exports them so imports stay ergonomic:
`from deal_document_intelligence.contracts import CanonicalDocument, ClauseUnit`.
"""

from deal_document_intelligence.contracts.bbox import BBox
from deal_document_intelligence.contracts.block import Block
from deal_document_intelligence.contracts.block_type import BlockType
from deal_document_intelligence.contracts.canonical_document import CanonicalDocument
from deal_document_intelligence.contracts.clause_type import ClauseType
from deal_document_intelligence.contracts.clause_unit import ClauseUnit
from deal_document_intelligence.contracts.entity import Entity
from deal_document_intelligence.contracts.entity_type import EntityType
from deal_document_intelligence.contracts.event import Event
from deal_document_intelligence.contracts.evidence_backed_result import (
    EvidenceBackedResult,
)
from deal_document_intelligence.contracts.evidence_span import EvidenceSpan
from deal_document_intelligence.contracts.extractions import Extractions
from deal_document_intelligence.contracts.obligation import Obligation
from deal_document_intelligence.contracts.relation import Relation
from deal_document_intelligence.contracts.relation_type import RelationType

__all__ = [
    "BBox",
    "Block",
    "BlockType",
    "CanonicalDocument",
    "ClauseType",
    "ClauseUnit",
    "Entity",
    "EntityType",
    "Event",
    "EvidenceBackedResult",
    "EvidenceSpan",
    "Extractions",
    "Obligation",
    "Relation",
    "RelationType",
]
