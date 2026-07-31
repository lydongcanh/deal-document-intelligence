from __future__ import annotations

from pydantic import BaseModel


class ParsedMarker(BaseModel):
    """A marker parsed into a comparable numeric path.

    `path` is the primary interpretation, for example
    "1.1" -> (1, 1), "ARTICLE III" -> (3,), "(b)" -> (2,).
    Parenthesized lower-case tokens are ambiguous (is "(i)" alpha i=9 or roman one?),
    so we keep the roman reading in `alt_path` and let the sequence decide.
    Decimal paths embed the parent numbers (Section 3.2 -> (3, 2)),
    which lets simple path arithmetic recover article-to-section nesting for free.
    """

    family: str
    path: tuple[int, ...]
    alt_path: tuple[int, ...] | None = None
