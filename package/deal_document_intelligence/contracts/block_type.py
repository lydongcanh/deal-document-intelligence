"""Structural role of a block, as reported by the parser."""

from __future__ import annotations

from enum import StrEnum


class BlockType(StrEnum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    LIST_ITEM = "list_item"
    TABLE = "table"
    PAGE_HEADER = "page_header"
    PAGE_FOOTER = "page_footer"
    CAPTION = "caption"
    OTHER = "other"
