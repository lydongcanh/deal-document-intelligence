from __future__ import annotations

from pydantic import BaseModel, Field

from deal_document_intelligence.contracts.clause_type import ClauseType


class ClausePrediction(BaseModel):
    """One (clause type, score) prediction — the typed unit of multi-label output.

    A `ClauseClassification` carries a list of these (every label above threshold,
    scored) plus a primary `clause_type` convenience field. This replaces stuffing
    predictions into an untyped `meta` dict.
    """

    clause_type: ClauseType
    score: float = Field(ge=0.0, le=1.0)
