from __future__ import annotations

from pydantic import BaseModel, Field


class Candidate(BaseModel):
    """A candidate boundary anchor: a place a clause might start.

    Candidates are internal to segmentation, not a cross-stage contract. Each keeps
    an exact offset into `ParsedDocument.text`, so a selected boundary maps straight
    back to source (`document.text[source_offset:] starts with marker_text`).

    A candidate is only a *possible* boundary. Whether it is real is decided later by
    the numbering grammar and the constrained decoder.
    """

    id: str
    source_offset: int = Field(ge=0, description="char offset into ParsedDocument.text")
    block_id: str
    marker_text: str
    marker_family: str
    at_block_start: bool = Field(
        description="marker is the first non-space text of its block"
    )
