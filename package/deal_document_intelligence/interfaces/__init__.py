"""Stage interfaces — the Protocols that define the pipeline's contract.

One Protocol per stage. Consumers implement these; the package never depends on
any vendor. Commodity stages (parse/OCR, language ID, value normalisation) are
usually satisfied by wrapping a library; the deal-specific stages are where we
add value.

    Parser               source file      -> ParsedDocument             [buy]
    LanguageDetector     document         -> DetectedLanguage            [buy/light]
    DocumentTypeDetector document         -> DetectedDocumentType        [build, not built yet]
    ClauseSegmenter      document         -> SegmentedClause[]           [build]
    ClauseClassifier     clauses          -> ClauseClassification[]      [build]
    EntityExtractor      document+clauses -> entities                    [hybrid]
    RelationExtractor    entities         -> obligations/events/rels     [build]
    EntityResolver       entities         -> normalised/resolved         [hybrid]
    DealAggregator       many documents   -> DealIntelligence            [build]
"""

from deal_document_intelligence.interfaces.clause_classifier import ClauseClassifier
from deal_document_intelligence.interfaces.deal_aggregator import DealAggregator
from deal_document_intelligence.interfaces.document_type_detector import (
    DocumentTypeDetector,
)
from deal_document_intelligence.interfaces.entity_extractor import EntityExtractor
from deal_document_intelligence.interfaces.language_detector import LanguageDetector
from deal_document_intelligence.interfaces.parser import Parser
from deal_document_intelligence.interfaces.relation_extractor import RelationExtractor
from deal_document_intelligence.interfaces.entity_resolver import EntityResolver
from deal_document_intelligence.interfaces.clause_segmenter import ClauseSegmenter

__all__ = [
    "Parser",
    "LanguageDetector",
    "DocumentTypeDetector",
    "ClauseSegmenter",
    "ClauseClassifier",
    "EntityExtractor",
    "RelationExtractor",
    "EntityResolver",
    "DealAggregator",
]
