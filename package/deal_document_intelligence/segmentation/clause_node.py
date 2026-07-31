from __future__ import annotations

from pydantic import BaseModel, Field


class ClauseNode(BaseModel):
    """A node in the clause tree produced by the decoder.

    Records where a clause starts (marker and source offset), its place in the
    hierarchy (depth, parent), and, once materialised, its extent:

    - inclusive span [source_offset, char_end): the clause plus all descendants.
    - direct_spans: the clause's OWN text, descendants removed; a list because a
      parent's sentence can resume after a sub-list.
    """

    id: str
    marker_text: str
    path: tuple[int, ...]
    depth: int = Field(ge=0)
    parent_id: str | None = None
    source_offset: int = Field(
        ge=0, description="offset of the marker in ParsedDocument.text (clause start)"
    )
    char_end: int | None = Field(
        default=None, description="inclusive-span end; None until materialised"
    )
    direct_spans: list[tuple[int, int]] = Field(
        default_factory=list, description="the clause's own text, descendants excluded"
    )
