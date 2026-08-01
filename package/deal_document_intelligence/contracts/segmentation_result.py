"""Stage 4 (segmentation) output: the clause tree plus how much to trust it.

Bundling the confidence with the clauses is the fail-safe. A consumer cannot take
the clauses without also seeing whether the segmentation should be routed to
review or a coarser fallback, so an out-of-distribution document is never silently
mis-segmented downstream.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from deal_document_intelligence.contracts.segmentation_confidence import (
    SegmentationConfidence,
)
from deal_document_intelligence.contracts.segmented_clause import SegmentedClause


class SegmentationResult(BaseModel):
    clauses: list[SegmentedClause] = Field(default_factory=list)
    confidence: SegmentationConfidence
