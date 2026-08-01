"""A clause's classification: stage 5 (classification) output.

References the clause by `clause_id` rather than embedding or subclassing it, so
segmentation output (`SegmentedClause`) and classification stay separate contracts and
each is fully populated for its stage. A consumer joins the two by id when it
wants "clause plus its type".
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from deal_document_intelligence.contracts.clause_prediction import ClausePrediction
from deal_document_intelligence.contracts.clause_type import ClauseType


class ClauseClassification(BaseModel):
    clause_id: str = Field(description="id of the SegmentedClause this classifies")
    clause_type: ClauseType = Field(
        description="primary (top) type; UNKNOWN when no type clears its threshold"
    )
    classification_confidence: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="score of the primary type; None when the type is UNKNOWN",
    )
    predictions: list[ClausePrediction] = Field(
        default_factory=list, description="all labels above threshold, scored (multi-label)"
    )
    model_version: str | None = Field(
        default=None, description="model/version that produced this classification"
    )
