from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from deal_document_intelligence.contracts.clause_role import ClauseRole
from deal_document_intelligence.contracts.evidence_span import EvidenceSpan


class SegmentedClause(BaseModel):
    """A segmented clause: stage 4 (segmentation) output.

    Structural only. It carries the clause's text, offsets, evidence, and its place
    in the tree. Classification is a separate stage with its own contract
    (`ClauseClassification`, keyed by `id`), so this type never holds fields that a
    later stage fills in and a consumer never has to guess which fields are live.
    """

    id: str
    text: str = Field(description="inclusive text: the clause plus all its sub-parts")
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    number: str | None = Field(default=None, description="clause number, e.g. '5.1'")
    heading: str | None = None
    # Hierarchy (first-class, not buried in meta): a caller can walk the tree or
    # pick a granularity (only sections) without re-parsing numbers.
    depth: int = Field(
        default=0, ge=0, description="0 = article, 1 = section, deeper = sub-part"
    )
    parent_id: str | None = Field(
        default=None, description="parent clause id; None at the top"
    )
    path: list[int] = Field(
        default_factory=list, description="numeric path, e.g. [5, 1] for 5.1"
    )
    role: ClauseRole | None = Field(
        default=None, description="article / section / subclause"
    )
    direct_spans: list[tuple[int, int]] = Field(
        default_factory=list,
        description="the clause's OWN text spans, its descendants removed; a list "
        "because a parent sentence can resume after a sub-list",
    )
    meta: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_span(self) -> SegmentedClause:
        if self.char_end < self.char_start:
            raise ValueError(f"char_end {self.char_end} < char_start {self.char_start}")
        return self
