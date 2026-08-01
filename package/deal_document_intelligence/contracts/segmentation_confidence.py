"""How much to trust a document's clause segmentation — the fail-safe signal.

Segmentation is deterministic and works well on well-structured agreements, but a
document whose numbering, reading order, or layout is unlike anything the rules
handle must not be silently mis-segmented. This score, computed from general
structural cues (no gold needed), lets a caller route a low-confidence document to
human review or a coarser fallback instead of trusting a broken tree.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SegmentationConfidence(BaseModel):
    """A per-document trust score for a clause segmentation, plus a review gate.

    The score combines signals that do not need the answer: whether articles run
    in order, whether section numbers are unique, and whether the tree passes its
    invariants. `needs_review` is the gate; `reasons` say why it tripped.
    """

    score: float = Field(ge=0.0, le=1.0, description="overall confidence, 1 = trust")
    needs_review: bool = Field(description="route to review or fallback when True")
    signals: dict[str, float] = Field(
        default_factory=dict, description="named sub-signals, each in [0, 1]"
    )
    reasons: list[str] = Field(
        default_factory=list, description="human-readable causes when flagged"
    )
