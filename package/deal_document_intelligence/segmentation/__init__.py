"""Clause segmentation (BUILD, differentiator) — see docs/04-segment-clauses.md.

Phase 1 (in progress): the deterministic core. Currently: candidate anchors.
Next: numbering grammar, constrained decoder, exact-span materializer.
"""

from deal_document_intelligence.segmentation.candidate import Candidate
from deal_document_intelligence.segmentation.candidate_anchors import generate_candidates
from deal_document_intelligence.segmentation.clause_node import ClauseNode
from deal_document_intelligence.segmentation.confidence import (
    REVIEW_THRESHOLD,
    assess_confidence,
)
from deal_document_intelligence.segmentation.deterministic_clause_segmenter import DeterministicClauseSegmenter
from deal_document_intelligence.segmentation.decoder import body_start_index, decode
from deal_document_intelligence.segmentation.numbering import (
    is_child_start,
    is_sibling_successor,
    parse_marker,
    starts_sequence,
)
from deal_document_intelligence.segmentation.parsed_marker import ParsedMarker
from deal_document_intelligence.segmentation.spans import clause_tree, materialize_spans
from deal_document_intelligence.segmentation.validation import validate_tree

__all__ = [
    "Candidate",
    "generate_candidates",
    "ParsedMarker",
    "parse_marker",
    "is_sibling_successor",
    "is_child_start",
    "starts_sequence",
    "ClauseNode",
    "DeterministicClauseSegmenter",
    "decode",
    "body_start_index",
    "materialize_spans",
    "clause_tree",
    "validate_tree",
    "assess_confidence",
    "REVIEW_THRESHOLD",
]
