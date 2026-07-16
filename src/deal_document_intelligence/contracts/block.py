"""One structural unit of a document (a paragraph, heading, table, …).

`char_start`/`char_end` index into `CanonicalDocument.text`, so a block's text
is exactly `document.text[char_start:char_end]`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from deal_document_intelligence.contracts.bbox import BBox
from deal_document_intelligence.contracts.block_type import BlockType


class Block(BaseModel):
    id: str
    type: BlockType = BlockType.PARAGRAPH
    text: str
    page: int = Field(ge=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    level: int | None = Field(default=None, description="heading level, if a heading")
    bbox: BBox | None = None
    meta: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_span(self) -> Block:
        if self.char_end < self.char_start:
            raise ValueError(f"char_end {self.char_end} < char_start {self.char_start}")
        return self
