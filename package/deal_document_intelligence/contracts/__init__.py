"""Typed data contracts passed between pipeline stages — the backbone.

One class per module; this package re-exports them so imports stay ergonomic:
`from deal_document_intelligence.contracts import ParsedDocument, SegmentedClause`.
"""

from deal_document_intelligence.contracts.bbox import BBox
from deal_document_intelligence.contracts.block import Block
from deal_document_intelligence.contracts.block_type import BlockType
from deal_document_intelligence.contracts.parsed_document import ParsedDocument
from deal_document_intelligence.contracts.canonical_entity import CanonicalEntity
from deal_document_intelligence.contracts.clause_category import (
    METADATA_TYPES,
    PROVISION_TYPES,
    ClauseCategory,
    category_of,
)
from deal_document_intelligence.contracts.clause_classification import ClauseClassification
from deal_document_intelligence.contracts.clause_prediction import ClausePrediction
from deal_document_intelligence.contracts.clause_role import ClauseRole
from deal_document_intelligence.contracts.clause_type import LABEL_SCHEMA, ClauseType
from deal_document_intelligence.contracts.segmented_clause import SegmentedClause
from deal_document_intelligence.contracts.deal_intelligence import DealIntelligence
from deal_document_intelligence.contracts.detected_document_type import (
    DetectedDocumentType,
)
from deal_document_intelligence.contracts.detected_language import (
    DetectedLanguage,
)
from deal_document_intelligence.contracts.document_type import DocumentType
from deal_document_intelligence.contracts.entity import Entity
from deal_document_intelligence.contracts.entity_mention import EntityMention
from deal_document_intelligence.contracts.entity_type import EntityType
from deal_document_intelligence.contracts.event import Event
from deal_document_intelligence.contracts.evidence_backed_result import (
    EvidenceBackedResult,
)
from deal_document_intelligence.contracts.evidence_span import EvidenceSpan
from deal_document_intelligence.contracts.obligation import Obligation
from deal_document_intelligence.contracts.relation import Relation
from deal_document_intelligence.contracts.relation_extraction import RelationExtraction
from deal_document_intelligence.contracts.relation_type import RelationType
from deal_document_intelligence.contracts.segmentation_confidence import (
    SegmentationConfidence,
)
from deal_document_intelligence.contracts.segmentation_result import SegmentationResult
from deal_document_intelligence.contracts.validation_issue import ValidationIssue

__all__ = [
    "BBox",
    "Block",
    "BlockType",
    "LABEL_SCHEMA",
    "METADATA_TYPES",
    "PROVISION_TYPES",
    "ParsedDocument",
    "CanonicalEntity",
    "ClauseCategory",
    "ClauseClassification",
    "ClausePrediction",
    "ClauseRole",
    "ClauseType",
    "SegmentedClause",
    "category_of",
    "DealIntelligence",
    "DetectedDocumentType",
    "DetectedLanguage",
    "DocumentType",
    "Entity",
    "EntityMention",
    "EntityType",
    "Event",
    "EvidenceBackedResult",
    "EvidenceSpan",
    "Obligation",
    "Relation",
    "RelationExtraction",
    "RelationType",
    "SegmentationConfidence",
    "SegmentationResult",
    "ValidationIssue",
]
